# Hardware compatibility

Only report combinations that were tested on physical hardware. A successful Python test or Docker build does not establish iDRAC or fan-command compatibility.

| Dell model | iDRAC generation / firmware | OS | GPU | Deployment | Result | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| PowerEdge R730 | Not recorded | Not recorded | Not recorded | Not recorded | Historically reported as tested; revalidation required for the next release | Existing project README |

Submit additional results with the hardware compatibility issue template. Remove service tags, serial numbers, public addresses, credentials, hostnames, and other identifying data.

## Required release evidence

Before a combination is listed as verified for a release, record:

- exact Dell model;
- iDRAC generation and firmware;
- operating system and version;
- GPU vendor/model and driver family;
- systemd or Docker deployment;
- manual-to-automatic restoration result;
- missing-sensor fail-safe result;
- sustained-load temperature and fan observations, without identifying data.
