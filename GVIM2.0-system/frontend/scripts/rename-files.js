import fs from "fs";
import path from "path";

const filesToRename = [
  {
    oldPath: "src/content/en/introduction/why-deerflow.mdx",
    newPath: "src/content/en/introduction/why-gvim.mdx"
  },
  {
    oldPath: "src/content/zh/introduction/why-deerflow.mdx",
    newPath: "src/content/zh/introduction/why-gvim.mdx"
  },
  {
    oldPath: "src/content/en/tutorials/deploy-your-own-deerflow.mdx",
    newPath: "src/content/en/tutorials/deploy-your-own-gvim.mdx"
  },
  {
    oldPath: "src/content/zh/tutorials/deploy-your-own-deerflow.mdx",
    newPath: "src/content/zh/tutorials/deploy-your-own-gvim.mdx"
  }
];

filesToRename.forEach(({ oldPath, newPath }) => {
  if (fs.existsSync(oldPath)) {
    fs.renameSync(oldPath, newPath);
    console.log(`Renamed: ${oldPath} -> ${newPath}`);
  } else {
    console.log(`Skipped (not found): ${oldPath}`);
  }
});

console.log("File renaming complete!");
