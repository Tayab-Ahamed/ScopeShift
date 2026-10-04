import { FileBlob, PresentationFile } from '@oai/artifact-tool';
const source = 'C:/Users/tayab/Downloads/Copy of HackSprint PPT Presentation.pptx';
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const snapshot = await presentation.inspect({kind:'slide,textbox,shape,image,table,chart,notes,layout', maxChars:30000});
console.log(snapshot.ndjson);
