def get_systems_list(self, prefix):
    systems = []
    for system_name in ["windows", "mac", "linux"]:
        if getattr(self, prefix + system_name) is None:
            return None
        elif getattr(self, prefix + system_name):
            systems.append(system_name)
    return systems

def set_systems_list(self, prefix, systems):
    for system_name in ["windows", "mac", "linux"]:
        if system_name in systems:
            setattr(self, prefix + system_name, True)
        else:
            setattr(self, prefix + system_name, False)
