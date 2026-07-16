
# design

Initially we started with a serverless solution
* single server (Streamlit). The initial solution. It works for single developers but is only useful for smoke-testing. This is now low priority.

The current design (which includes 3 separate servers) is a client-server system:
* client/frontend server + backend(FastAPI server+ AIserver). This is our current system

* front end server (windows, style, etc.) Aleena + ? new intern/s
* AI server (REST, LLM, RAG, Groq/Ollama servers)
 * FastAPI server: Udita + ? intern/s
 * semantic CABook PMR

There are several components to testing. Note: it is always possible that a user with unusual operating system, or libraries, etc. will crash :

* smoke-testing - does it work without immediate crashing ( https://en.wikipedia.org/wiki/Smoke_testing_(software))? 

# components 

* client server: smoke-tested
* backend server: smoke-tested
* network-testing - can the system be accessed by any user without special permissions. smoke-tested
* simple query and window display - smoke-tested
* semantic content (LLM chunking, links to book, etc.) - Smoke tested
* window display. Clean separation of concerns (HTML/CSS/JS, etc.) smoke-tested
* backend 

* Content: Does the bot retrieve useful content? Smoke-tested (in that the answer appears to be possibly relevant). This has NOT been evaluated thoroughly
* Hallucinations: Smoke-tested Not enough use to report, 

## backend
One major block is the backend server.

Note this is complex and simple Wordpress etc won't work.

There  are several possible production solutions but none are trivial:

1 rent server space (e.g. Amazon). I've never done this and I don't know about financing/lockin
2 Cambridge chemistry. I used to have a server but I don't know if it can be resurrected
3 Cambridge HPC or other AI service. Can be paid out from PMR budget. Not yet investigated
4 NIPGR. Udita and colleagues are investigating this but the lead time is probably beyond June 10
5 OKF server. Solana, can OKF help here?

I will investigate 2 for tomorrow's meeting.

Note: These servers are NOT trivial . They must be up permanently, be secure (attacks, resources). This means they are under non-project management that we don't control who will have rules for edits and new versions. Therefore in the initial stages I think we need 

* persistent paid managed server (e.g. Amazon)
* lightweight ephemeral free server (our current solution - requirements from PMR+Cursor)

Both require domain names or IP

The lightweight server is currently provided by CloudflareTunnel. A personal machine (e.g. PMRLaptop) runs a service on Cloudflare which looks like a server to the world. It is rapid to close/reboot (< 1 minute) and does not expose (my) content. 

Upsides:
It has worked for a number of people.
Has Python scripts to launch and close.
Any of the team can launch their own server

Downsides:
Goes down  when Iaptop is closed, crashes or taken off air.
A different URL for each reboot
Messy to launch and edit

Solana,
I'd be very grateful for reactions and suggestions

P.




