// FrameNet data schema
// I mostly use JavaScript syntax here because that is how my frontend and backend are designed
//
// @author: Dmetri Hayes/Nimkiins MikZaabii
// @date: 2024-03-12

// some frames need to be excluded
const BAD_FRAME_NAMES = ['Test35', 'Test_the_test', 'Boulder'];
const BAD_FRAME_IDS = [398, 100, 427];

// 1. FRAME INDEX
// A. get the frames data
var stmt = `SELECT * FROM frame WHERE Name NOT IN (${BAD_FRAME_NAMES.map(x => '"' + x + '"').join(',')})`

// 2. LEXICAL UNIT INDEX
// A. get the lexical unit data
// filter out LUs in the test frames
var stmt = `SELECT * FROM lexunit WHERE Frame_ref NOT IN (${BAD_FRAME_IDS.join(',')})`

// 3. FRAME VIEW
// A. get the frame data
var stmt = `SELECT * FROM frame WHERE ID = ?`

// B. get associated frame element data
var stmt = `SELECT * FROM frameelement WHERE Frame_ref = ?`
// NOTE: for the web view, we are removing Core-Unexpressed and just calling it Core 

// C. get associated frame relation data
// there are different ways to do this. 
// I load all of them at once and then filter based on "child" frames,
var stmt = `SELECT * FROM framerelation`
var frs = db.all(stmt);
var stmt = `SELECT * FROM relationtype`
var rts = db.all(stmt);
frs.filter(x => x['SuperFrame_Ref'] == props.frameID)
.forEach(fr => {
  // get the frame relation type
  var rt = rts.filter(x => x['ID'] == fr['RelationType_Ref'])[0];
  // get the subframe
  var subFrame = frames.filter(x => x['ID'] == fr['SubFrame_Ref'])[0];
  // ... CREATE list item
})
// and then deal with "parent" frames
frs.filter(x => x['SubFrame_Ref'] == props.frameID)
.forEach(fr => {
  // get the frame relation type
  var rt = props.rts.filter(x => x['ID'] == fr['RelationType_Ref'])[0];
  // get the subframe
  var superFrame = props.frames.filter(x => x['ID'] == fr['SuperFrame_Ref'])[0];
  // ... CREATE list item
});

// D. get associated lexical unit data
var stmt = `SELECT * FROM lexunit`
var lus = db.all(stmt);
lus.filter(x => x['Frame_Ref'] == props.frameID)
  .sort((a, b) => a['Name'] > b['Name'] ? 1 : -1) // alphabetize
  .forEach(lu => {
    // ... CREATE list item
  });

// E. get the color data
// XXX: I use a cached mapping of color data, which uses more vivid colors (though there are conflicts
// on some frames with very many frame elements)
// the base colors are in Color, which are referenced
// in the FgColorS_Ref, BgColorS_Ref, FgColorP_Ref, and BgColorP_Ref fields of the LabelType table
// I don't have a procedure to fetch these readily available right now


// 4. LEXICAL UNIT VIEW
// The website currently has two lexical unit pages: Lexical entry and the Annotation
// The Lexical entry page contains (the Frame name,) Definition and Semantic Type alongside the valence information

// The Annotation page contains the frame element table, and sets of annotated sentences
// REMINDER: for the web view of the frame elements, we are removing Core-Unexpressed and just calling it Core
// The annotation data is the main data used for both pages.

// A. get the annotation data
// instead of a full breakdown, I have added my "build_annotation_data.py" file for now
// IMPORTANT NOTE: line 64-70 and 95-96 (and associated constants) may be unnecessary.
// I was extracting UNANN annotation sets so that I could have part-of-speech information.
// This info is presumably used in the existing reports to determine the preposition in the valence table 
// (for an example, see "PP[by].Dep" on the Lexical entry of abandon.v from Abandonment)
// However, Michael Elsworth has said this process is tricky due to the messiness of the part-of-speech tags, 
// and advises that we just use a look-up table 