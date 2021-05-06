# pdf-text-analysis
This tool is used for 
  - ~text processing and analysis of multiple folders of multiple PDF files~ (currently not working)
  - Combining search results from multiple journal databases and annotating articles with journal rankings

## Problem
  - Google Scholar too often returns "unscholarly" articles.
  - Using "scholarly" journal databases results in duplicates and combining multiple search results into a single spreadsheet

## Use Case
If a researcher had two research questions:  
`RQ1: How are literature reviews automated?`  
`RQ2: What are the meta concepts of literature reviews?` 

Then search keyword sets would look something like:  
`SKS1: (literature AND review) AND (automated)`  
`SKS2: (literature AND review) AND (meta)`  

Searching for these SKSs across five journal databases would result in **10 result sets** which would then have to be:  
1. Checked for duplicates  
2. Checked for journal reputation  
3. Combined into a single usable spreadsheet  

By using this tool, these 10 result sets still must be searched and downloaded, but steps 1-3 are now automated.

## Example
1. Download this codebase
2. Go to webofknowledge.com and search for `(literature AND review) AND (automated)`. 
3. Click on "Export" and download the Excel file of the results.
4. Create a folder in `input` called `sks1`
5. Move your downloaded file into `sks1`
6. Repeat the previous on scopus.com
7. Repeat the previous with the search `(literature AND review) AND (meta)` and folder name `sks2`
8. Run the program
9. Open `combined_searches.xlsx` and see that your search keyword set results have been combined, duplicates have been removed, journal rankings have been assigned, and the data has been normalized.

## Installation and Execution
1. Check that `python` and `git` are properly installed. If not, google how to do that.  
2. Check that `pip` is installed. If not, google how to do that.  
3. Run `pip install -r requirements.txt`
4. Run `python3 runner.py`

## TODOS
* Keyword search functionality across folders/pdfs
* Make metadata an xlsx file instead of json for better UX
