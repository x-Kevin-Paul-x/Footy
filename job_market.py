class JobMarket:
    def __init__(self):
        self.available_managers = []

    def add_manager(self, manager):
        if manager not in self.available_managers:
            self.available_managers.append(manager)

    def remove_manager(self, manager):
        if manager in self.available_managers:
            self.available_managers.remove(manager)

    def get_available_managers(self):
        return self.available_managers
