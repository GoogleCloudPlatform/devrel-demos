/**
 * @OnlyCurrentDoc
 *
 * The above comment directs Apps Script to limit the scope of file access for this script
 * to only the current document. This is a best practice for security.
 */

/**
 * Creates a custom menu in the Google Docs UI when the document is opened.
 */
function onOpen() {
  DocumentApp.getUi()
      .createMenu('Image Tools')
      .addItem('Extract & Save Images', 'extractAndSaveImages')
      .addToUi();
}

/**
 * Extracts all inline images from the current document and saves them to a new folder in Google Drive.
 */
function extractAndSaveImages() {
  const doc = DocumentApp.getActiveDocument();
  const body = doc.getBody();
  const images = body.getImages();
  const ui = DocumentApp.getUi();

  if (images.length === 0) {
    ui.alert('No images found in this document.');
    return;
  }

  // Create a folder in the root of the user's Drive.
  // The folder will be named "Images from [Document Name]".
  const docName = doc.getName();
  const folder = DriveApp.createFolder(`Images from ${docName}`);

  let savedCount = 0;
  images.forEach((image, i) => {
    try {
      const blob = image.getBlob();
      const contentType = blob.getContentType();
      
      // Determine the file extension from the content type.
      let extension = '';
      if (contentType === 'image/png') {
        extension = '.png';
      } else if (contentType === 'image/jpeg') {
        extension = '.jpg';
      } else if (contentType === 'image/gif') {
        extension = '.gif';
      } else {
        // Fallback for other image types, though less common in Docs.
        extension = '.unknown';
      }

      // Pad the number with leading zeros (e.g., 1 -> 001).
      const fileNumber = String(i + 1).padStart(3, '0');
      const fileName = `image${fileNumber}${extension}`;
      
      // Set the name of the blob before creating the file
      blob.setName(fileName);

      folder.createFile(blob);
      savedCount++;
    } catch (e) {
      // Log errors for debugging, e.g., if an image is inaccessible.
      console.error(`Could not save image ${i + 1}: ${e.toString()}`);
    }
  });

  // Provide feedback to the user.
  const message = `${savedCount} of ${images.length} images have been saved to the folder "${folder.getName()}" in your Google Drive.`;
  ui.alert('Extraction Complete', message, ui.ButtonSet.OK);
}
