
![](https://travis-ci.org/gambl/ro-python.svg)

ro-python library

This repository is a partial fork of [ro-manager](https://github.com/wf4ever/ro-manager) in order to
- Separate out core RO python tooling from the ro-manager
- Refactor what was there as a general, re-useable ro library
- Bring the tooling in line with the RO Bundle specification @ https://researchobject.github.io/specifications/bundle/

## Example

```python
#!/usr/bin/env python3
from rolib.bundle import *
from rolib.manifest import *
import datetime

with Bundle("test.bundle.zip",mode='w') as ro:

    ro.manifest.createdOn = datetime.datetime.now().isoformat()
    # Stian created the reserarch object (this collection)
    stian = Agent(name="Stian Soiland-Reyes", orcid="http://orcid.org/0000-0001-9842-9718")
    ro.manifest.createdBy = stian


    ro.writestr("hello.txt", "To be, or not to be, that is the question")
    hello = ro.manifest.get_aggregate("hello.txt")

    # Stian created the hello.txt resource
    hello.createdBy = stian
    hello.createdOn = datetime.datetime.now().isoformat()
    ## but someone else authored its content:
    shakespeare = Agent(name="William Shakespeare", uri="http://dbpedia.org/page/William_Shakespeare")
    hello.authoredBy = shakespeare
    hello.authoredOn = datetime.datetime(1604,1,1).isoformat()

    # Aggregate an external resource, also different author
    quote = ro.manifest.add_aggregate("http://www.folgerdigitaltexts.org/?chapter=5&play=Ham&loc=line-3.1.64")
    quote.authoredBy = shakespeare
    # Folger Shakespeare Library made the digital representation
    folger = Agent(name="Folger Shakespeare Library", uri="http://www.folgerdigitaltexts.org/?chapter=0&?target=credit")
    quote.createdBy = folger


    # This wikipage (which we didn't need to aggregate) is somewhat about this quote
    ro.manifest.add_annotation(about=quote.uri, content="https://en.wikipedia.org/wiki/To_be,_or_not_to_be")
    # And also about our hello.txt - even if it doesn't mention it by URL
    ro.manifest.add_annotation(about="hello.txt", content="https://en.wikipedia.org/wiki/To_be,_or_not_to_be")
```
