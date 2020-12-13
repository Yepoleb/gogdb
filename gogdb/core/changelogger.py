import copy

import gogdb.core.model as model

class Changelogger:
    def __init__(self, prod_new, prod_old, timestamp):
        self.prod_new = prod_new
        self.prod_old = prod_old
        self.timestamp = timestamp
        self.entries = []

    def property(self, name):
        value_new = getattr(self.prod_new, name)
        value_old = getattr(self.prod_old, name)
        if value_new != value_old:
            if value_old is None:
                action = "add"
            elif value_new is None:
                action = "del"
            else:
                action = "change"
            self.entries.append(model.ChangeRecord(
                product_id = self.prod_new.id,
                timestamp = self.timestamp,
                action = action,
                category = "property",
                property_record = model.PropertyRecord(
                    property_name = name,
                    value_new = value_new,
                    value_old = value_old
                )
            ))

    @staticmethod
    def strip_download(download):
        """Remove file information to make download smaller"""
        stripped = copy.copy(download)
        stripped.files = None
        return stripped

    def downloads(self, name):
        downloads_new = getattr(self.prod_new, "dl_" + name)
        downloads_old = getattr(self.prod_old, "dl_" + name)

        dl_map_new = {dl.unique_id: dl for dl in downloads_new}
        dl_map_old = {dl.unique_id: dl for dl in downloads_old}
        dl_ids_both = set(dl_map_new.keys()) | set(dl_map_old.keys())

        for dl_id in dl_ids_both:
            in_new = dl_id in dl_map_new
            in_old = dl_id in dl_map_old
            dl_rec = model.DownloadRecord(dl_type=name)

            if in_new and in_old:
                dl_new = self.strip_download(dl_map_new[dl_id])
                dl_old = self.strip_download(dl_map_old[dl_id])
                action = "change"
                if dl_new.is_same(dl_old):
                    continue
            elif in_new:
                dl_new = self.strip_download(dl_map_new[dl_id])
                dl_old = None
                action = "add"
            else:
                dl_new = None
                dl_old = self.strip_download(dl_map_old[dl_id])
                action = "del"



            if isinstance(dl_new, model.BonusDownload) or isinstance(dl_old, model.BonusDownload):
                dl_rec.dl_new_bonus = dl_new
                dl_rec.dl_old_bonus = dl_old
            else:
                dl_rec.dl_new_software = dl_new
                dl_rec.dl_old_software = dl_old

            self.entries.append(model.ChangeRecord(
                product_id = self.prod_new.id,
                timestamp = self.timestamp,
                action = action,
                category = "download",
                download_record = dl_rec
            ))

    def builds(self):
        builds_new = self.prod_new.builds
        builds_old = self.prod_old.builds

        build_ids_new = set(build.id for build in builds_new)
        build_ids_old = set(build.id for build in builds_old)
        build_ids_added = build_ids_new - build_ids_old
        for added_id in build_ids_added:
            self.entries.append(model.ChangeRecord(
                product_id = self.prod_new.id,
                timestamp = self.timestamp,
                action = "add",
                category = "build",
                build_id = added_id
            ))

    def prod_added(self):
        self.entries.append(model.ChangeRecord(
            product_id = self.prod_new.id,
            timestamp = self.timestamp,
            action = "add",
            category = "product"
        ))
