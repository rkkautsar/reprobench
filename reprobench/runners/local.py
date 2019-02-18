import os
import itertools
from pathlib import Path
from datetime import datetime
from peewee import SqliteDatabase
from reprobench.core.bases import Runner
from reprobench.core.db import (db, db_bootstrap, Run, Tool, ParameterCategory, Task)
from reprobench.utils import import_class

class LocalWorker(threading.Thread):
    def run():

class LocalRunner(Runner):
    def __init__(self, config):
        self.config = config
        now = datetime.now()
        self.timestamp = now.strftime("%Y%m%d-%H%M%S")
    
    def setup(self):
        database = SqliteDatabase(f"{self.config['title']}_{self.timestamp}.db")
        db.initialize(database)
        db_bootstrap(self.config)

    def create_working_directory(self, tool_name, parameter_category, task_category, filename):
        path = Path("./output") / tool_name / parameter_category / task_category / filename
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run(self):
        self.setup()
        for tool_name, tool_module in self.config['tools'].items():
            ToolClass = import_class(tool_module)
            tool_instance = ToolClass()
            tool_instance.setup()
            
            for (parameter_category, parameter), (task_category, task) in itertools.product(self.config['parameters'].items(), self.config['tasks'].items()):
                # only folder task type for now
                assert task['type'] == "folder"

                files = Path().glob(task['path'])
                for file in files:
                    context = self.config.copy()
                    context['working_directory'] = self.create_working_directory(tool_name, parameter_category, task_category, file.name)
                    context['tool'] = tool_instance
                    context['parameter'] = parameter
                    context['task_category'] = task_category
                    context['task'] = {
                        "type": "file",
                        "path": str(file.resolve())
                    }

                    tool = Tool.get(Tool.module == tool_module)
                    parameter_category = ParameterCategory.get(ParameterCategory.title == parameter_category)
                    task = Task.get(Task.path == str(file))

                    run = Run.create(
                        tool= tool,
                        task = task,
                        parameter_category = parameter_category,
                    )

                    context['run'] = run
                    
                    for runstep in self.config['steps']['run']:
                        Step = import_class(runstep['step'])
                        step = Step()
                        step.run(context)
            
            tool_instance.teardown()

