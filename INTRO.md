
# INTRODUCTION to CABot

**NOTE: Prospective interns should read this BEFORE interviews!**

## Why this workshop is different!

Everyone can now *ask* an AI a question but it's much harder to be sure the answer is *correct*! We're building this chatbot to be **trustable**. That's why the interns are not only building the bot, but *testing* it and *validating* the output.

## for (prospective) interns
Interns will have a background in using a Python IDE, developing code, testing it, and making it available publicly on Github. Interns will help each other when difficulties arise.

Interns will work *as a a team*, validating each other's work and practising good communication:

### **synchronously** 

e.g. Zoom and similar technology. It is VERY important to be as fluent as possible:
  * microphone and video *switched ON by default*
  * talking conversationally, no pauses.  There is no hierarchy , we are all equals
  * recording ON by default. We publish to the group (not the world)
  
### **asynchronously** 
 * Slack as the immediate channel for recording temporary (1-month) information
 * Github as the longterm record. ALL Interns should use the following `git` commands effortlessly:
   - `status` (for current state)
   - `clone` (from existing remote repo)
   - `add` or `delete` 
   - `commit` 
   - `pull` and `push`
   - `branch` (to create/select a branch). All interns will create their own branch
   - `merge` (with project agreement)

## software

All software is Open Source and where possible we use Local Open models (e.g. HuggingFace) rather than cloud services.

## content testing and validation

**This is critical**

AIs frequently hallucinate and give answers that look right but are wrong in one or more respects. We are using RAG (Retrieval Augmented Generation https://en.wikipedia.org/wiki/Retrieval-augmented_generation) to constrain the answers to be based on our ground truth documents (CA Book, IPCC, Wikimedia). Every answer should point to core references and contain paragraph IDs. We will provide hyperlinks which means the user can **validate** the answers. 

## teamwork and collaborative discipline

This short chatbot project depends on everyone collaborating. This includes:

* **publishing all progress daily**. This is critical. We record:
  - what I/we did since last time
  - what I/we are going to do
  - what's blocking me/us
 If you don't do this it **actually harms** the project
* agreed structure and naming of files. 
* testing and validating current work before doing new stuff
* reviewing code and documents. 100 lines of good output is better than 10000 lines of AI slop.

## helping others learn, including tutorials

We'll have many people using the chatbot who are ignorant of how AI works and how to use it. Helping others learn, often with notebook or video tutorials,  is one of the most valuable contributions. 
