import path from 'node:path';
import fs from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { PresentationFile } from '@oai/artifact-tool';

const SKILL_DIR = 'C:/Users/tayab/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const workspaceDir = 'C:/Projects/Scope Shift';
const candidatePath = path.join(workspaceDir, '.ppt-build', 'scopeshift-draft.pptx');
const finalPath = path.join(workspaceDir, 'submission', 'ScopeShift-HackSprint-Phase2.pptx');
const stagingDir = path.join(workspaceDir, '.codex-finalizer');
await fs.mkdir(stagingDir, {recursive:true});
await fs.mkdir(path.dirname(finalPath), {recursive:true});
const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, 'container_tools/artifact_tool_utils.mjs')).href);
const result = await finalizePresentation({
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable: 'C:/Users/tayab/AppData/Local/Programs/Python/Python313/python.exe',
  integrityValidatorPath: path.join(SKILL_DIR, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(SKILL_DIR, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '24384000,13716000', '--validate-bullet-geometry', '--validate-heading-fit'],
  sourceTemplatePath: 'C:/Users/tayab/Downloads/Copy of HackSprint PPT Presentation.pptx',
  requiredTemplateReferenceSlides: [1,2,3,4,5,6,7],
  minimumTemplateCoverageRatio: 1,
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, 'ScopeShift-HackSprint-Phase2.validation.json'),
});
console.log(JSON.stringify(result, null, 2));
