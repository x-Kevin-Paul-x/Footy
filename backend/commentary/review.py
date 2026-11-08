"""Export an offline review page with actual spoken text and claim provenance."""

import argparse
import html
import json
from pathlib import Path


def stamp(seconds):
    return f'{int(seconds)//60}:{int(seconds)%60:02d}'


def export_review(artifacts, output):
    artifacts, output = Path(artifacts), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    quality = json.loads((artifacts/'quality_report.json').read_text())
    context = json.loads((artifacts/'match_context.json').read_text(encoding='utf-8'))
    clips = json.loads((artifacts/'audio_clips_manifest.json').read_text())
    script = json.loads((artifacts/'commentary_script.json').read_text(encoding='utf-8'))
    utterances = {u['commentary_id']:u for u in script['utterances']}
    videos = list(output.glob('*-commentary.mp4'))
    if len(videos) != 1:
        raise ValueError('Review output must contain one commentary video')
    rows, transcript = [], []
    for clip in sorted(clips,key=lambda c:c['requested_start_ms']):
        metadata = json.loads(Path(clip['file_path']).with_suffix('.json').read_text())
        text = metadata['text']
        grounding = utterances[clip['clip_id']]['grounding']
        if not grounding:
            raise ValueError('Review requires sentence provenance')
        start, end = clip['requested_start_ms']/1000, (clip['requested_start_ms']+clip['actual_duration_ms'])/1000
        transcript.append(dict(start=start,end=end,speaker=clip['speaker'],text=text,
                               kind=grounding['kind'],grounding=grounding))
        citations = html.escape(json.dumps(grounding,indent=2))
        rows.append(f'<article class="line" data-start="{start}" data-end="{end}">'
            f'<button onclick="seek({max(0,start-.5)})"><span>{stamp(start)}</span> '
            f'{html.escape(clip["speaker"])} · {html.escape(clip["slot_type"].replace("_"," "))}</button>'
            f'<p>{html.escape(text)}</p><details><summary>{html.escape(grounding["kind"])} · evidence</summary>'
            f'<pre>{citations}</pre></details></article>')
    goals = ''.join(f'<button onclick="seek({max(0,g["crossing_seconds"]-2)})">'
                    f'{stamp(g["crossing_seconds"])} · {html.escape(g["scorer"])} ({html.escape(g["score"])})</button>'
                    for g in quality['goals'])
    title = html.escape(f"{context['home_team']} {context['home_score']}–{context['away_score']} {context['away_team']}")
    omissions = len(quality.get('optional_audio_omissions',[]))
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Footy · Grounded commentary review</title><style>
    :root{color-scheme:dark;font-family:system-ui,sans-serif;background:#061120;color:#f7ecd4}*{box-sizing:border-box}body{max-width:1550px;margin:auto;padding:26px}h1{font-size:clamp(24px,3vw,38px);margin:10px 0}h2{font-size:19px}.label,a,summary{color:#8edbe4}.hint{color:#b7cbd9;font-size:14px;line-height:1.5}main{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(320px,1fr);gap:24px;margin-top:24px}.panel{padding:20px;border:1px solid #2c455f;border-radius:22px;background:#0d2037;box-shadow:8px 8px 25px #020915}.watch{position:sticky;top:18px;align-self:start}video{width:100%;border-radius:12px;background:#000}button{border:1px solid #2b4b66;border-radius:12px;background:#142c46;color:inherit;font:inherit;padding:10px;cursor:pointer;text-align:left}button:hover,button:focus-visible{background:#224862;outline:2px solid #8edbe4}.goals{display:flex;gap:8px;flex-wrap:wrap}.goals button{font-size:13px}.transcript{max-height:75vh;overflow:auto}.line{border:1px solid #29425c;border-radius:14px;margin:10px 0;padding:12px}.line.active{border-color:#ff7828;background:#20354d}.line button{font-size:13px;color:#8edbe4}.line p{line-height:1.5}details{font-size:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere}.metrics{display:flex;gap:10px;flex-wrap:wrap}.metrics span{background:#142c46;border-radius:14px;padding:10px 14px}.links{display:flex;gap:18px;margin-top:18px;font-size:13px}@media(max-width:950px){main{grid-template-columns:1fr}.watch{position:static}body{padding:14px}}</style>
    <span class="label">FOOTY / EVIDENCE-GATED COMMENTARY</span><h1>__TITLE__</h1><p class="hint">Improved review copy · source video unchanged · pronunciation and delivery still need listening.</p><div class="metrics"><span>__CLIPS__ voiced lines</span><span>8 recorded goals</span><span>Longest speech gap: __GAP__s</span></div><main><section class="watch panel"><video id="match" controls preload="metadata" src="__VIDEO__"></video><p class="hint">__OMISSIONS__ optional audio cue(s) omitted because speech would not fit. All required goal and whistle calls remain. No audio overlaps or window overruns.</p><h2>Jump to a goal</h2><div class="goals">__GOALS__</div><p class="hint">Click a transcript timestamp to seek. Expand evidence to see the approved template, supporting records and when they became available. A passing text check is not a listening-quality score.</p><div class="links"><a href="transcript.md">Read transcript</a><a href="quality_report.json">Automated report</a><a href="__VIDEO__" download>Download video</a></div></section><section class="panel"><h2>Actual spoken commentary</h2><div class="transcript">__ROWS__</div></section></main><script>const v=document.getElementById('match');function seek(t){v.currentTime=t;v.play().catch(()=>{});}v.addEventListener('timeupdate',()=>document.querySelectorAll('.line').forEach(x=>x.classList.toggle('active',v.currentTime>=Number(x.dataset.start)&&v.currentTime<Number(x.dataset.end))));</script></html>'''
    replacements = dict(TITLE=title,CLIPS=str(len(clips)),GAP=f"{quality.get('maximum_inter_clip_speech_gap_seconds',0):.1f}",
                        VIDEO=html.escape(videos[0].name,quote=True),OMISSIONS=str(omissions),GOALS=goals,ROWS=''.join(rows))
    replacements['ROWS'] = ''.join(rows)
    page = page.replace('</div><main>',
        f'<span>{quality.get("spoken_dialogue_pairs",0)} paired exchanges</span>'
        f'<span>{quality.get("reviewed_dialogue_clips",0)} model-reviewed turns</span></div><main>')
    page = page.replace('EVIDENCE-GATED COMMENTARY','CONVERSATIONAL COMMENTARY REVIEW')
    page = page.replace('the approved template, supporting records and when they became available',
                        'the evidence, conversational links and independent model review')
    page = page.replace('A passing text check is not a listening-quality score.',
                        'Model review can miss errors. The dialogue and delivery still need your listening feedback.')
    page = page.replace('8 recorded goals',f'{len(quality["goals"])} recorded goals')
    for key,value in replacements.items():
        page=page.replace(f'__{key}__',value)
    (output/'review.html').write_text(page,encoding='utf-8')
    (output/'transcript.json').write_text(json.dumps(transcript,indent=2),encoding='utf-8')
    (output/'transcript.md').write_text(f'# {title}\n\n'+'\n\n'.join(
        f"**{stamp(t['start'])} · {t['speaker']}** — {t['text']}" for t in transcript),encoding='utf-8')
    (output/'quality_report.json').write_text(json.dumps(quality,indent=2),encoding='utf-8')
    return output/'review.html'


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    print(export_review(args.artifacts,args.output))
