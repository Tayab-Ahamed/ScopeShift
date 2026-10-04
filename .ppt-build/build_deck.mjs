import fs from 'node:fs/promises';
import path from 'node:path';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const source = 'C:/Users/tayab/Downloads/Copy of HackSprint PPT Presentation.pptx';
const workspaceDir = 'C:/Projects/Scope Shift';
const buildDir = path.join(workspaceDir, '.ppt-build');
const outputDir = path.join(workspaceDir, 'submission');
await fs.mkdir(outputDir, {recursive:true});

const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const family = 'Aptos';
const ink = '#17211B';
const green = '#236B4A';
const red = '#A33D32';
const cream = '#F7F5EE';

function textbox(slide, text, left, top, width, height, size=28, color=ink, bold=false) {
  const box = slide.shapes.add({geometry:'textbox', position:{left, top, width, height}, fill:'none', line:{fill:'none', width:0}});
  box.text = text;
  box.text.style = {typeface:family, fontSize:size, color, bold, autoFit:'shrink'};
  return box;
}
function card(slide, title, body, left, top, width, height, color=cream) {
  const box = slide.shapes.add({geometry:'roundRect', position:{left, top, width, height}, fill:color, line:{fill:'#D8DDD6', width:1}});
  box.text = `${title}\n${body}`;
  box.text.style = {typeface:family, fontSize:25, color:ink, bold:false, autoFit:'shrink'};
  return box;
}
function title(slide, value) { slide.placeholders.getItem('title').text = value; }

const s1 = presentation.slides.getItem(0);
for (const id of ['sh/8j2xsbmd','sh/l4by5wv6','sh/654ze1wr','sh/76dg76dc','sh/87mhgbex','sh/m90f2hwn','sh/na9gvmd8','sh/kratwza5']) {
  try { const obj = presentation.resolve(id); if (id === 'sh/8j2xsbmd') obj.text = 'ScopeShift';
    if (id === 'sh/l4by5wv6') obj.text = 'Evidence-governed BRD generation';
    if (id === 'sh/654ze1wr') obj.text = 'PS42';
    if (id === 'sh/76dg76dc') obj.text = 'A working product path';
    if (id === 'sh/87mhgbex') obj.text = 'HACK SPRINT';
    if (id === 'sh/m90f2hwn') obj.text = '17–18 OCTOBER 2026';
    if (id === 'sh/na9gvmd8') obj.text = '24-hour build';
    if (id === 'sh/kratwza5') obj.text = 'TEAM: SCOPE SHIFT\n\nTRACK: PS42';
  } catch {}
}
s1.speakerNotes.textFrame.setText('ScopeShift: evidence-governed BRD generation. No unmeasured performance claims are made.');

const s2 = presentation.slides.getItem(1); presentation.resolve('sh/3ilkjepk').text = 'The problem';
card(s2, 'One checkout feature', 'BRD: UPI only\nScreenshot: Card button visible\nClient note: Card is in scope', 120, 340, 500, 340, '#F3E8E1');
card(s2, 'The failure mode', 'AI can summarize all three sources.\nIt cannot safely decide what becomes a requirement without an explicit authority rule.', 700, 340, 500, 340, '#E8EFE9');
textbox(s2, 'The missing layer is governance.', 1260, 410, 500, 120, 42, green, true);
s2.speakerNotes.textFrame.setText('Scenario is the product fixture in the repository. Claims describe the test scenario, not measured customer prevalence.');

const s3 = presentation.slides.getItem(2); presentation.resolve('sh/ulwfitor').text = 'The solution';
card(s3, '1  Extract', 'Gemini returns structured claims, quotes, and proposed scope changes.', 120, 310, 380, 300, '#E8EFE9');
card(s3, '2  Validate', 'Code checks schema, claim allowlist, and quote provenance.', 560, 310, 380, 300, '#F2EBDD');
card(s3, '3  Resolve', 'The resolver computes the current BRD from active evidence and events.', 1000, 310, 380, 300, '#E8EFE9');
card(s3, '4  Explain', 'Every requirement shows what governed it, what it replaced, and why it disappeared.', 1440, 310, 360, 300, '#F2EBDD');
s3.speakerNotes.textFrame.setText('Gemini is an extractor. Authority is decided in application code.');

const s4 = presentation.slides.getItem(3); textbox(s4, 'Live proof: DISPUTED → GOVERNED → DISPUTED', 108, 88, 1600, 150, 46, ink, true);
card(s4, '01  DISPUTED', 'BRD and screenshot conflict.\nRequirement withheld.', 120, 360, 480, 320, '#F3E8E1');
card(s4, '02  GOVERNED', 'Verified client note authorizes Card.\nRequirement enters the BRD.', 720, 360, 480, 320, '#E8EFE9');
card(s4, '03  DISPUTED', 'Decision removed.\nResolver recomputes from remaining evidence.', 1320, 360, 480, 320, '#F3E8E1');
s4.speakerNotes.textFrame.setText('This state transition is covered by the repository tests and the local browser demo.');

const s5 = presentation.slides.getItem(4); presentation.resolve('sh/5sz6l0ry').text = 'Data flow';
card(s5, 'Sources', 'PDF · screenshot · client note', 120, 330, 330, 250, '#F2EBDD');
card(s5, 'Evidence', 'Structured claims with validated quotes', 520, 330, 330, 250, '#E8EFE9');
card(s5, 'Event log', 'BigQuery in production architecture\nSQLite in the local demo', 920, 330, 330, 250, '#F2EBDD');
card(s5, 'Resolver', 'Deterministic projection of the current BRD', 1320, 330, 330, 250, '#E8EFE9');
textbox(s5, 'Evidence → event log → resolver → current BRD', 370, 720, 1200, 80, 34, green, true);
s5.speakerNotes.textFrame.setText('The local demo reads through a replayed snapshot. BigQuery is the persisted append-only log in the target architecture.');

const s6 = presentation.slides.getItem(5); presentation.resolve('sh/mt4z29oj').text = 'Prototype screen';
card(s6, 'Sources', 'SRC-01  BRD\nSRC-02  Screenshot\nSRC-03  Client note', 120, 310, 390, 350, '#F2EBDD');
card(s6, 'Event log', '1  ADDED  SRC-01\n2  ADDED  SRC-02\n3  ADDED  SRC-03\n4  REMOVED  SRC-03', 590, 310, 460, 350, '#E8EFE9');
card(s6, 'Current BRD', 'DISPUTED\n\nRequirement withheld\n\nReason: no active governing decision', 1130, 310, 580, 350, '#F3E8E1');
textbox(s6, 'The judge can watch the requirement appear and disappear from the same evidence history.', 220, 760, 1500, 70, 31, green, true);
s6.speakerNotes.textFrame.setText('The screenshot is represented by the working local browser UI. Replace this slide with an actual screenshot after the UI is opened and captured.');

const s7 = presentation.slides.getItem(6); presentation.resolve('sh/wrmlsfed').text = 'Validation';
card(s7, 'Verified now', 'Core replay tests\nInvalid transition checks\nHTTP integration flow\nSecurity headers and bounded input', 120, 300, 500, 360, '#E8EFE9');
card(s7, 'Pending evidence', 'Gemini plain baseline\nGemini hinted baseline\nFinal captured UI screenshot\nOrganizer ruling on pre-build scope', 720, 300, 500, 360, '#F2EBDD');
card(s7, 'Build-window demo', 'Ingest the client note live, with a one-click pre-extracted fallback if the API is unavailable on stage.', 1320, 300, 440, 360, '#E8EFE9');
s7.speakerNotes.textFrame.setText('No baseline metric is included because the API key and fixtures are not yet available.');

const draft = path.join(buildDir, 'scopeshift-draft.pptx');
await (await PresentationFile.exportPptx(presentation)).save(draft);
const montage = await presentation.export({format:'webp', montage:true, scale:1});
await fs.writeFile(path.join(buildDir, 'scopeshift-montage.webp'), new Uint8Array(await montage.arrayBuffer()));
console.log(draft);
