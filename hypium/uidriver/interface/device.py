class Device:

    def execute_shell_command(self, command, timeout=30000):
        pass

    def execute_connector_command(self, command, timeout=30000):
        pass

    def pull_file(self, remote_path, local_path):
        pass

    def push_file(self, local_path, remote_path):
        pass

    def model(self):
        pass
