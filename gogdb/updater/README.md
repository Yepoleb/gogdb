# Updater post processing scripts

Updater post processing scripts follow a common interface. They have to provide a class that gets instanciated after the downloader has finished, but before any other processing code is run. The `wants` variable specifies what kind of data they need. When running just a subset of scripts only the required files are loaded. Processing is done in the following three stages:

* `prepare` - Can be used for any kind of async initialization code, that can not be run in the synchronous constructor.
* `process` - Called individually for each product. The data variable contains the requested product data if it exists. Each field should individually be checked for `None` before access. This step requires a lot of skipping on missing data.
* `finish` - This is were the final result is generated and usually saved to disk.

```py
class Processor:
    wants: set = {"product", "changelog", "prices"}

    def __init__(self, db: gogdb.core.storage.Storage):
        self.db = db

    async def prepare(self):
        pass

    async def process(self, data: ProcessorData):
        pass

    async def finish(self):
        pass
```

The interface of the `ProcessorData` class:

```py
@dataclass
class ProcessorData:
    id: int
    product: model.Product = None
    changelog: List[model.ChangeRecord] = None
    prices: List[model.PriceRecord] = None
```

This is far from a proper plugin interface and only handles the data processing without presentation. It might become more powerful as requirements become more clear.
