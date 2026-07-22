from investhome_api.worker.settings import WorkerSettings

j = WorkerSettings.cron_jobs[0]
print(type(j))
print([a for a in dir(j) if not a.startswith("_")])
print("name=", getattr(j, "name", None))
