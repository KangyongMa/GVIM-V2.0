import fs from "fs";
import path from "path";

const targetDirs = [
  "src",
];

const targetFiles = [
  "next.config.js",
  "package.json",
  "README.md",
];

function walk(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  list.forEach((file) => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    if (stat && stat.isDirectory()) {
      if (file !== "node_modules" && file !== ".next") {
        results = results.concat(walk(filePath));
      }
    } else {
      results.push(filePath);
    }
  });
  return results;
}

const fileExtensions = [".mdx", ".md", ".ts", ".tsx", ".js", ".jsx", ".json"];

let allFiles = [];

targetDirs.forEach((dir) => {
  if (fs.existsSync(dir)) {
    allFiles = allFiles.concat(walk(dir));
  }
});

targetFiles.forEach((file) => {
  if (fs.existsSync(file)) {
    allFiles.push(file);
  }
});

let updatedFilesCount = 0;

allFiles.forEach((file) => {
  const ext = path.extname(file);
  if (!fileExtensions.includes(ext) && !targetFiles.includes(file)) {
    return;
  }

  try {
    const content = fs.readFileSync(file, "utf8");
    let newContent = content;

    // Define replacements
    // 1. DeerFlow -> GVIM
    newContent = newContent.replace(/DeerFlow/g, "GVIM");
    // 2. DEERFLOW -> GVIM
    newContent = newContent.replace(/DEERFLOW/g, "GVIM");
    // 3. DEER_FLOW -> GVIM
    newContent = newContent.replace(/DEER_FLOW/g, "GVIM");
    // 4. deer-flow -> gvim
    newContent = newContent.replace(/deer-flow/g, "gvim");
    // 5. deerflow -> gvim
    newContent = newContent.replace(/deerflow/g, "gvim");

    if (newContent !== content) {
      fs.writeFileSync(file, newContent, "utf8");
      console.log(`Updated: ${file}`);
      updatedFilesCount++;
    }
  } catch (error) {
    console.error(`Error processing ${file}:`, error);
  }
});

console.log(`\nSuccessfully processed all files. Updated ${updatedFilesCount} files to GVIM.`);
