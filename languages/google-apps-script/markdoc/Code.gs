/**
 * @OnlyCurrentDoc
 */

function onOpen() {
  DocumentApp.getUi()
    .createMenu('Markdoc')
    .addItem('Render Markdown', 'renderMarkdown')
    .addToUi();
}

/**
 * @OnlyCurrentDoc
 */

function onOpen() {
  DocumentApp.getUi()
    .createMenu('Markdoc')
    .addItem('Render Markdown', 'renderMarkdown')
    .addToUi();
}

function renderMarkdown() {
  const doc = DocumentApp.getActiveDocument();
  const body = doc.getBody();
  const paragraphs = body.getParagraphs();
  
  let inBlock = false;
  let currentBlock = [];
  const blocksToProcess = [];
  
  // 1. Scan and Collect Blocks
  // We iterate a snapshot, but we will remove fences immediately.
  // Note: removing fences doesn't affect the reference to the content paragraphs 
  // we are collecting, but it does affect document indices. 
  // However, since we work with Element objects, we should be safe.
  
  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i];
    const text = p.getText().trim();
    
    if (text === '```markdown') {
      inBlock = true;
      p.removeFromParent(); // Remove start fence
      continue;
    }
    
    if (inBlock && text === '```') {
      inBlock = false;
      p.removeFromParent(); // Remove end fence
      if (currentBlock.length > 0) {
        blocksToProcess.push(currentBlock);
      }
      currentBlock = [];
      continue;
    }
    
    if (inBlock) {
      currentBlock.push(p);
    }
  }
  
  // 2. Process collected blocks
  for (const blockElements of blocksToProcess) {
    let elements = blockElements;
    
    // Structure Processing
    elements = processTables(elements);
    processHeadings(elements);
    elements = processLists(elements);
    
    // Inline Processing
    cleanUpSyntax(elements);
    processLinks(elements);
  }
}

/**
 * Table Processing
 * Consumes paragraphs, creates tables, returns flattened list of active elements (including new table cells).
 */
function processTables(elements) {
  const newElements = [];
  let i = 0;
  
  while (i < elements.length) {
    const p = elements[i];
    
    // Check if this paragraph is the start of a table
    if (isTableParam(p)) {
      // Look ahead in the *provided list* to see the extent of the table
      let rows = [];
      let k = i;
      while (k < elements.length && isTableParam(elements[k])) {
        rows.push(elements[k].getText());
        k++;
      }
      
      // Validate table (needs header and separator)
      if (rows.length >= 2 && rows[1].includes('---')) {
        // Create table using the first paragraph as anchor
        const table = createTable(p, rows);
        
        // Remove the original paragraphs from doc
        for (let j = i; j < k; j++) {
          elements[j].removeFromParent();
        }
        
        // Add new table content to our processing list.
        // We want to process text inside the table (bold, links, etc.)
        // So we extract all paragraphs from the table cells.
        const tableParagraphs = getTableParagraphs(table);
        newElements.push(...tableParagraphs);
        
        // Skip consumed rows
        i = k; 
      } else {
        // Not a valid table, just keep the paragraph
        newElements.push(p);
        i++;
      }
    } else {
      newElements.push(p);
      i++;
    }
  }
  return newElements;
}

function isTableParam(element) {
  if (element.getType() !== DocumentApp.ElementType.PARAGRAPH) return false;
  const text = element.getText().trim();
  return text.startsWith('|') && text.endsWith('|');
}

function createTable(sibling, rows) {
  const parent = sibling.getParent();
  const index = parent.getChildIndex(sibling);
  
  // Parse Data
  const tableData = rows.map(row => {
    // Remove outer pipes
    const content = row.trim().substring(1, row.trim().length - 1);
    return content.split('|').map(c => c.trim());
  });
  
  // Filter out the separator row (index 1)
  const header = tableData[0];
  const data = tableData.slice(2);
  const finalData = [header, ...data];
  
  const table = parent.insertTable(index);
  
  // Remove default empty row
  if (table.getNumRows() > 0) table.removeRow(0);
  
  for (let r = 0; r < finalData.length; r++) {
    const tableRow = table.appendTableRow();
    for (let c = 0; c < finalData[r].length; c++) {
      tableRow.appendTableCell(finalData[r][c]);
    }
  }
  
  // Style Header
  const headerRow = table.getRow(0);
  for (let c = 0; c < headerRow.getNumCells(); c++) {
      headerRow.getCell(c).setBackgroundColor('#eeeeee').setBold(true);
  }
  
  return table;
}

function getTableParagraphs(table) {
  const paras = [];
  const numRows = table.getNumRows();
  for (let r = 0; r < numRows; r++) {
    const row = table.getRow(r);
    const numCells = row.getNumCells();
    for (let c = 0; c < numCells; c++) {
      const cell = row.getCell(c);
      const numChildren = cell.getNumChildren();
      for (let k = 0; k < numChildren; k++) {
        const child = cell.getChild(k);
        if (child.getType() === DocumentApp.ElementType.PARAGRAPH) {
          paras.push(child);
        }
      }
    }
  }
  return paras;
}

/**
 * Headings
 */
function processHeadings(elements) {
  for (const p of elements) {
    if (p.getType() !== DocumentApp.ElementType.PARAGRAPH) continue;
    
    const text = p.getText();
    const match = text.match(/^(#{1,6})\s+(.*)/);
    if (match) {
      const level = match[1].length;
      const content = match[2];
      
      p.setText(content);
      
      switch (level) {
        case 1: p.setHeading(DocumentApp.ParagraphHeading.HEADING1); break;
        case 2: p.setHeading(DocumentApp.ParagraphHeading.HEADING2); break;
        case 3: p.setHeading(DocumentApp.ParagraphHeading.HEADING3); break;
        case 4: p.setHeading(DocumentApp.ParagraphHeading.HEADING4); break;
        case 5: p.setHeading(DocumentApp.ParagraphHeading.HEADING5); break;
        case 6: p.setHeading(DocumentApp.ParagraphHeading.HEADING6); break;
      }
    }
  }
}

/**
 * Lists
 */
function processLists(elements) {
  const newElements = [];
  
  for (const p of elements) {
    if (p.getType() !== DocumentApp.ElementType.PARAGRAPH) {
      newElements.push(p);
      continue;
    }
    
    const text = p.getText();
    
    // Bullet list: - or *
    const bulletMatch = text.match(/^[\-\*]\s+(.*)/);
    if (bulletMatch) {
      const content = bulletMatch[1];
      const parent = p.getParent();
      const index = parent.getChildIndex(p);
      
      // Remove paragraph, insert ListItem
      p.removeFromParent();
      const listItem = parent.insertListItem(index, content);
      listItem.setGlyphType(DocumentApp.GlyphType.BULLET);
      
      newElements.push(listItem);
      continue;
    }
    
    // Numbered list: 1.
    const numMatch = text.match(/^\d+\.\s+(.*)/);
    if (numMatch) {
      const content = numMatch[1];
      const parent = p.getParent();
      const index = parent.getChildIndex(p);
      
      p.removeFromParent();
      const listItem = parent.insertListItem(index, content);
      listItem.setGlyphType(DocumentApp.GlyphType.NUMBER);
      
      newElements.push(listItem);
      continue;
    }
    
    newElements.push(p);
  }
  return newElements;
}

/**
 * Inline Formatting
 */
function cleanUpSyntax(elements) {
  // BOLD
  processRegexAndFormat(elements, "\\*\\*([^\\*]+)\\*\\*", (text, start, end) => {
    text.setBold(start, end, true);
  });
  
  // ITALIC
  processRegexAndFormat(elements, "\\*([^\\*]+)\\*", (text, start, end) => {
    text.setItalic(start, end, true);
  });
   
  // CODE
  processRegexAndFormat(elements, "`([^`]+)`", (text, start, end) => {
    text.setFontFamily(start, end, 'Consolas'); 
    text.setBackgroundColor(start, end, '#f0f0f0'); 
  });
}

function processRegexAndFormat(elements, pattern, formatFn) {
  for (const element of elements) {
    // Only process text containers
    if (element.getType() !== DocumentApp.ElementType.PARAGRAPH && 
        element.getType() !== DocumentApp.ElementType.LIST_ITEM) continue;
        
    let found = element.findText(pattern);
    while (found) {
      const textObj = found.getElement().asText();
      const fullText = textObj.getText();
      const start = found.getStartOffset();
      const end = found.getEndOffsetInclusive();
      
      const matchString = fullText.substring(start, end + 1);
      const jsRegex = new RegExp(pattern); 
      const match = matchString.match(jsRegex);
      
      if (match && match[1]) {
        const content = match[1];
        
        textObj.deleteText(start, end);
        textObj.insertText(start, content);
        
        const newEnd = start + content.length - 1;
        if (newEnd >= start) {
            formatFn(textObj, start, newEnd);
        }
      }
      
      found = element.findText(pattern);
    }
  }
}

function processLinks(elements) {
   const pattern = "\\[([^\\]]+)\\]\\(([^\\)]+)\\)";
   
   for (const element of elements) {
     if (element.getType() !== DocumentApp.ElementType.PARAGRAPH && 
         element.getType() !== DocumentApp.ElementType.LIST_ITEM) continue;

     let found = element.findText(pattern);
     while (found) {
       const textObj = found.getElement().asText();
       const fullText = textObj.getText();
       const start = found.getStartOffset();
       const end = found.getEndOffsetInclusive();
       
       const matchString = fullText.substring(start, end + 1);
       const jsRegex = new RegExp(pattern);
       const match = matchString.match(jsRegex);
       
       if (match) {
         const text = match[1];
         const url = match[2];
         
         textObj.deleteText(start, end);
         textObj.insertText(start, text);
         
         const newEnd = start + text.length - 1;
         textObj.setLinkUrl(start, newEnd, url);
         textObj.setForegroundColor(start, newEnd, '#1155cc');
         textObj.setUnderline(start, newEnd, true);
       }
       found = element.findText(pattern);
     }
   }
}
