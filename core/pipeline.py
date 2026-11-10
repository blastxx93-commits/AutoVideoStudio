"""Orquestrador: roteiro + título  →  vídeo pronto na pasta escolhida.
Uso direto:  python -m core.pipeline dados/trabalhos/<pasta_do_trabalho>
Se algo falhar no meio, rodar de novo continua de onde parou (arquivos prontos são reaproveitados)."""
import json
import random
import shutil
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import llm, tts, images, render, review, subtitles, thumbnail
from .config import load_settings, TRANSITIONS
from .utils import JobLogger, Cancelado, duration, safe_name


CHECKPOINT = [lambda: None]


def _parallel(fn, items, workers, log, label):
    errors = []
    done = [0]
    lock = threading.Lock()

    def wrap(it):
        try:
            CHECKPOINT[0]()
            fn(it)
        except Cancelado:
            raise
        except Exception as e:
            errors.append((it.get("id"), str(e)))
        with lock:
            done[0] += 1
            if done[0] % 5 == 0 or done[0] == len(items):
                log(f"  {label}: {done[0]}/{len(items)}")

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        list(ex.map(wrap, items))
    return errors


def distribuir_fontes(n: int, pct_banco: int, modo: str = "Intercalado") -> list:
    """Decide, cena a cena, se vem do banco ou da IA respeitando a porcentagem."""
    n_banco = round(n * pct_banco / 100)
    if modo == "Aleatório":
        lst = ["banco"] * n_banco + ["ia"] * (n - n_banco)
        random.shuffle(lst)
        return lst
    if modo == "Blocos":  # grupos de ~3 cenas seguidas da mesma fonte
        nb = -(-n // 3)
        blocos = distribuir_fontes(nb, pct_banco, "Intercalado")
        out = [b for b in blocos for _ in range(3)][:n]
        idx = list(range(n))
        while out.count("banco") > n_banco:  # ajuste fino para bater a porcentagem exata
            out[[i for i in idx if out[i] == "banco"][-1]] = "ia"
        while out.count("banco") < n_banco:
            out[[i for i in idx if out[i] == "ia"][-1]] = "banco"
        return out
    out, acc = [], 0.0  # Intercalado: espalha por igual
    for _ in range(n):
        acc += pct_banco
        if acc >= 100 - 1e-9:
            out.append("banco")
            acc -= 100
        else:
            out.append("ia")
    return out


def run_job(job_dir: Path):
    job_dir = Path(job_dir)
    job = json.loads((job_dir / "trabalho.json").read_text(encoding="utf-8"))
    (job_dir / "controle.json").unlink(missing_ok=True)
    L = JobLogger(job_dir)
    CHECKPOINT[0] = L.checkpoint
    s = load_settings()
    api_threads = int(s.get("threads_api", 4))
    try:
        (job_dir / "audio").mkdir(exist_ok=True)
        (job_dir / "midia").mkdir(exist_ok=True)
        (job_dir / "cenas").mkdir(exist_ok=True)
        scenes_file = job_dir / "cenas.json"

        # 1) cenas e prompts
        if scenes_file.exists():
            scenes = json.loads(scenes_file.read_text(encoding="utf-8"))
            L.info(f"Retomando trabalho com {len(scenes)} cenas.")
        else:
            L.step("Dividindo roteiro em cenas", 3)
            scenes = llm.split_scenes(job["roteiro"], float(job.get("segundos_por_cena", 6)))
            L.info(f"  {len(scenes)} cenas.")
            L.step("Criando prompts das imagens", 6)
            scenes = llm.make_prompts(scenes, job["titulo"], job["estilo_visual"], job.get("estilo_personalizado", ""), L.info,
                                      personagem=job.get("personagem_fixo", ""),
                                      direcao_ref=job.get("ref_direcao", ""))
        save = lambda: scenes_file.write_text(json.dumps(scenes, ensure_ascii=False, indent=1), encoding="utf-8")
        save()

        # 2) narração
        L.step("Gerando narração", 12)
        prov, voice = job["tts_provider"], job["voz_id"]

        def do_tts(sc, force=False):
            mp3 = job_dir / "audio" / f"c{sc['id']:04d}.mp3"
            wav = mp3.with_suffix(".wav")
            if force or not wav.exists():
                i = sc["id"] - 1
                prev = scenes[i - 1]["texto"] if i > 0 else ""
                nxt = scenes[i + 1]["texto"] if i + 1 < len(scenes) else ""
                tts.synth(prov, sc["texto"], voice, mp3, job, prev, nxt)
                tts.to_wav(mp3, wav, float(job.get("velocidade_voz", 1.0)))
            sc["wav"] = str(wav)
            sc["dur_audio"] = duration(wav)

        errs = _parallel(do_tts, scenes, min(3, api_threads), L.info, "narração")
        if errs:
            raise RuntimeError(f"Falha na narração da cena {errs[0][0]}: {errs[0][1]}")
        save()

        # 3) imagens / clipes
        L.step("Buscando/gerando imagens e clipes", 30)
        picker = images.StockPicker(job)
        pick_lock = threading.Lock()
        from .config import pct_banco
        pct = pct_banco(job)
        if any("fonte" not in sc for sc in scenes):
            fontes = distribuir_fontes(len(scenes), pct, job.get("distribuicao_mix", "Intercalado"))
            for sc, f in zip(scenes, fontes):
                sc["fonte"] = f
            L.info(f"  mistura: {fontes.count('banco')} cenas do banco + {fontes.count('ia')} cenas de IA")

        def gerar_ia(sc, base):
            p = images.full_prompt(sc["image_prompt"], job)
            return str(images.generate_ai(job["img_provider"], p, base, seed=random.randint(1, 10**8)))

        def do_media(sc, force=False, exclude=()):
            base = job_dir / "midia" / f"c{sc['id']:04d}"
            if not force and sc.get("midia") and Path(sc["midia"]).exists():
                return
            if sc.get("fonte") == "banco":
                try:
                    with pick_lock:
                        sc["midia"] = str(picker.pick(sc["search_query"], base, exclude))
                        sc["banco_id"] = getattr(picker, "last_key", "")
                    return
                except Exception as e:
                    if pct >= 100:
                        raise
                    L.info(f"  cena {sc['id']}: nada no banco ({str(e)[:60]}) → usando IA")
                    sc["fonte"] = "ia"
            sc["midia"] = gerar_ia(sc, base)

        workers = api_threads if pct < 100 else 2
        errs = _parallel(do_media, scenes, workers, L.info, "imagens")
        for sid, e in errs:  # nova tentativa
            L.info(f"  cena {sid} falhou ({e[:120]}); tentando de novo")
            try:
                do_media(scenes[sid - 1], force=True)
            except Exception as e2:
                raise RuntimeError(f"Não consegui mídia para a cena {sid}: {e2}")
        save()

        # 4) revisão das cenas
        report = []
        if job.get("revisao"):
            L.step("Agente de revisão: conferindo imagens e áudio", 45)
            for rnd in range(3 if job.get("revisao_auto_corrigir") else 1):
                issues = review.review_scenes(scenes, L.info)
                if job.get("revisao_ia_visao") and rnd == 0:
                    for k, v in review.ai_vision_check(scenes, L.info).items():
                        issues.setdefault(k, []).extend(v)
                if not issues:
                    L.info("  imagens OK ✔")
                    break
                for sid, probs in issues.items():
                    L.info(f"  cena {sid}: {', '.join(probs)}")
                    report.append(f"Cena {sid}: {', '.join(probs)}" + (" → corrigida" if job.get("revisao_auto_corrigir") and rnd < 2 else ""))
                if not job.get("revisao_auto_corrigir") or rnd == 2:
                    break
                for sid in issues:
                    sc = scenes[sid - 1]
                    if sc.get("manual"):
                        continue  # mídia escolhida por você no projeto: não troca sozinho
                    try:
                        do_media(sc, force=True, exclude={sc.get("banco_id")})
                    except Exception as e:
                        L.info(f"  não consegui trocar a cena {sid}: {e}")
            for sc in scenes:
                probs = review.check_scene_audio(sc)
                if probs:
                    L.info(f"  áudio da cena {sc['id']}: {', '.join(probs)} → regerando")
                    try:
                        do_tts(sc, force=True)
                        p2 = review.check_scene_audio(sc)
                        report.append(f"Áudio cena {sc['id']}: {', '.join(probs)}" + (" → corrigido" if not p2 else " → ainda com aviso"))
                    except Exception as e:
                        report.append(f"Áudio cena {sc['id']}: {', '.join(probs)} (não regerado: {e})")
            save()

        # 5) montagem das cenas
        from .config import RESOLUCOES
        VW, VH = RESOLUCOES.get(job.get("resolucao", ""), (1920, 1080))
        L.step(f"Animando as cenas ({VH}p)", 55)
        T = float(job.get("duracao_transicao", 0.5)) if TRANSITIONS.get(job["transicao"]) else 0.0
        trans = render.transitions_for(len(scenes) - 1, job["transicao"]) + [None]
        t = 0.0
        for i, sc in enumerate(scenes):
            sc["inicio"] = t
            t += sc["dur_audio"]
            # meia transição antes (menos a 1ª cena) e meia depois (menos a última): troca centrada na fala
            sc["dur_video"] = sc["dur_audio"] + (T / 2 if i > 0 else 0) + (T / 2 if i < len(scenes) - 1 else 0)
        total = t
        save()

        def do_render(sc):
            out = job_dir / "cenas" / f"c{sc['id']:04d}.mp4"
            marker = out.with_suffix(".ok")
            sig = f"{sc['midia']}|{Path(sc['midia']).stat().st_mtime:.0f}|{sc['dur_video']:.3f}|{job['movimento']}|{VW}"
            if out.exists() and marker.exists() and marker.read_text() == sig:
                sc["seg"] = str(out)
                return
            render.render_scene(Path(sc["midia"]), sc["dur_video"], out, job["movimento"], job.get("intensidade_movimento", "Média"), VW, VH)
            marker.write_text(sig)
            sc["seg"] = str(out)

        errs = _parallel(do_render, scenes, int(s.get("threads_render", 2)), L.info, "cenas animadas")
        if errs:
            raise RuntimeError(f"Falha ao animar a cena {errs[0][0]}: {errs[0][1]}")

        L.step("Aplicando transições", 72)
        video = render.merge([(sc["seg"], sc["dur_audio"], trans[i]) for i, sc in enumerate(scenes)], T,
                             job_dir / "video_sem_audio.mp4", log=L.info)

        # 6) áudio
        L.step("Mixando narração, música e efeitos", 80)
        narr = job_dir / "narracao.wav"
        render._concat_copy([sc["wav"] for sc in scenes], narr)
        render.ensure_default_sfx()
        sfx_times = [sc["inicio"] + sc["dur_audio"] - T / 2 for i, sc in enumerate(scenes[:-1]) if trans[i]] \
            if job.get("efeitos_sonoros") else []
        from . import trilha
        musicas, tema_trilha, creditos_trilha = trilha.selecionar(job, total, L.info)
        if musicas:
            L.info(f"  trilha: {tema_trilha or 'arquivo/pasta'} · {len(set(musicas))} música(s)")
        elif job.get("trilha_modo", "Automático") not in ("Sem música",):
            report.append(f"Sem trilha sonora: nenhuma música encontrada (tema: {tema_trilha})")
        job["_creditos_musica"] = creditos_trilha
        (job_dir / "trilha.json").write_text(json.dumps({"tema": tema_trilha, "musicas": [str(m) for m in musicas],
                                                         "creditos": creditos_trilha}, ensure_ascii=False), encoding="utf-8")
        audio = render.mix_audio(narr, total, job_dir / "audio_final.m4a", job, sfx_times, musics=musicas)

        # 7) legendas
        tpl, tpl_nome = {}, job.get("template", "Nenhum")
        if tpl_nome and tpl_nome != "Nenhum":
            from . import templates
            L.step(f"Aplicando template: {tpl_nome}", 84)
            tpl = templates.preparar(tpl_nome, job_dir, job["titulo"], job.get("template_rotulo", ""),
                                     job.get("template_fim", ""), job.get("template_fim_sub", ""))
            if not job.get("template_abertura", True):
                tpl.pop("abertura", None)
            if not job.get("template_encerramento", True):
                tpl.pop("encerramento", None)
            if not job.get("template_moldura", True):
                tpl.pop("moldura", None)
            if not job.get("template_cor", True):
                tpl.pop("cor", None)
            tpl["dur_abertura"] = float(job.get("template_dur_abertura", 4.0))

        events, ass = None, None
        if job.get("legendas"):
            L.step("Criando legendas", 85)
            ass = job_dir / "legendas.ass"
            override = None
            if tpl and job.get("template_legenda", True):
                from . import templates
                override = templates.legenda_override(tpl_nome)
            events = subtitles.build(scenes, job["estilo_legenda"], ass, job_dir / "legendas.srt", override=override)

        # 8) render final
        L.step("Renderizando vídeo final", 88)
        final = job_dir / "video_final.mp4"
        render.final_mux(video, audio, final, ass, total, tpl, (VW, VH))

        if job.get("revisao"):
            L.step("Agente de revisão: conferindo o vídeo final", 94)
            fr = review.review_final(final, total, events, L.info)
            report += [f"Vídeo final: {x}" for x in fr]
            if not fr:
                L.info("  vídeo final OK ✔")

        # 9) thumbnail
        thumb = None
        if job.get("thumbnail") and (job_dir / "thumbnail.jpg").exists():
            thumb = job_dir / "thumbnail.jpg"
            L.info("  thumbnail já pronta (reaproveitada)")
        elif job.get("thumbnail"):
            L.step("Gerando thumbnail", 96)
            try:
                idea = llm.thumbnail_idea(job["titulo"], job["roteiro"], job["estilo_visual"], job.get("personagem_fixo", ""))
                prompt = job.get("thumb_prompt") or idea["prompt"]
                texto = (job.get("thumb_texto") or "").strip() or idea["texto"]
                if texto.strip().lower() == "sem texto":
                    texto = ""
                bg = images.generate_ai(job.get("img_provider_thumb", job["img_provider"]),
                                        images.full_prompt(prompt, job), job_dir / "thumb_fundo")
                thumb = thumbnail.compose(bg, texto, job_dir / "thumbnail.jpg")
            except Exception as e:
                L.info(f"  thumbnail falhou: {e}")
                report.append(f"Thumbnail não gerada: {e}")

        # 9b) descrição, hashtags e palavras-chave
        if job.get("seo", True) and (job_dir / "seo.json").exists():
            L.info("  descrição já pronta (reaproveitada)")
        elif job.get("seo", True):
            L.step("Escrevendo descrição, hashtags e palavras-chave", 97)
            try:
                from . import seo
                r = seo.gerar(job, scenes, total, L.info)
                seo.salvar(r, job_dir)
                L.info(f"  {len(r['hashtags'])} hashtags · {len(r['palavras_chave'])} palavras-chave "
                       f"({len(r.get('buscadas', []))} são buscas reais do YouTube)")
            except Exception as e:
                L.info(f"  descrição falhou: {e}")
                report.append(f"Descrição não gerada: {e}")

        # 10) relatório + revisão humana ou exportação direta
        rel = [f"Relatório de revisão — {job['titulo']}", f"Duração: {total / 60:.1f} min · {len(scenes)} cenas", ""]
        rel += report or ["Nenhum problema encontrado ✔"]
        (job_dir / "relatorio_revisao.txt").write_text("\n".join(rel), encoding="utf-8")
        (job_dir / "relatorio.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        if job.get("revisar_antes", True):
            L.step("Gerando prévia para você assistir", 99)
            try:
                from .utils import run
                run(["ffmpeg", "-y", "-i", final, "-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "ultrafast",
                     "-crf", "30", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", job_dir / "previa.mp4"])
            except Exception as e:
                L.info(f"  prévia não gerada ({e}); a interface usará o vídeo final.")
            L.aguardando(str(final))
        else:
            exportar(job_dir, log=L.info)
            L.done(str(saida_video(job_dir, job)))
    except Cancelado:
        L.cancel()
    except Exception as e:
        L.info(traceback.format_exc()[-1500:])
        L.fail(str(e))
        raise


def saida_video(job_dir: Path, job: dict, pasta: str = None, sufixo: str = "") -> Path:
    base = Path((pasta or job["pasta_saida"]).strip().strip('"')) / safe_name(job["titulo"])
    return base / f"{safe_name(job['titulo'])}{sufixo}.mp4"


def exportar(job_dir: Path, pasta: str = None, log=print, resolucao: str = None) -> Path:
    """Copia vídeo, thumbnail, legenda e relatório para a pasta escolhida.
    resolucao: "1080p (Full HD)" ou "2K (1440p)". Se for diferente da usada na geração, o vídeo é convertido."""
    from .config import RESOLUCOES
    from .utils import run
    job_dir = Path(job_dir)
    job = json.loads((job_dir / "trabalho.json").read_text(encoding="utf-8"))
    gerado = job.get("resolucao", "1080p (Full HD)")
    resolucao = resolucao or gerado
    sufixo = "_2K" if resolucao.startswith("2K") else ""
    out_video = saida_video(job_dir, job, pasta, sufixo)
    dest = out_video.parent
    dest.mkdir(parents=True, exist_ok=True)
    name = out_video.stem.replace("_2K", "")
    if resolucao == gerado or resolucao not in RESOLUCOES:
        shutil.copy2(job_dir / "video_final.mp4", out_video)
    else:
        w, h = RESOLUCOES[resolucao]
        log(f"Convertendo para {resolucao}...")
        run(["ffmpeg", "-y", "-i", job_dir / "video_final.mp4", "-vf", f"scale={w}:{h}:flags=lanczos",
             "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "copy",
             "-movflags", "+faststart", out_video])
    if (job_dir / "thumbnail.jpg").exists():
        shutil.copy2(job_dir / "thumbnail.jpg", dest / f"{name}_thumbnail.jpg")
    if job.get("legendas") and job.get("exportar_srt") and (job_dir / "legendas.srt").exists():
        shutil.copy2(job_dir / "legendas.srt", dest / f"{name}.srt")
    if (job_dir / "relatorio_revisao.txt").exists():
        shutil.copy2(job_dir / "relatorio_revisao.txt", dest / "relatorio_revisao.txt")
    for f in ("descricao.txt", "palavras_chave.txt", "hashtags.txt"):
        if (job_dir / f).exists():
            shutil.copy2(job_dir / f, dest / f)
    log(f"Vídeo salvo em: {out_video}")
    return out_video


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    run_job(Path(sys.argv[1]))
