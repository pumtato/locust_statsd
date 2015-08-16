import time

from locust import Locust, events, task, TaskSet

import statsd_client


class LocustStatsdClient(statsd_client.StatsdClient):

    def __getattribute__(self, name):
        func = statsd_client.StatsdClient.__getattribute__(self, name)
        if name[0] == '_':
            return func

        if not hasattr(func, '__call__'):
            return func

        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                total_time = int((time.time() - start_time) * 1000)
                events.request_failure.fire(request_type="statsd", name=name, response_time=total_time, exception=e)
            else:
                total_time = int((time.time() - start_time) * 1000)
                events.request_success.fire(request_type="statsd", name=name, response_time=total_time, response_length=0)
        
        return wrapper


class StatsdLocust(Locust):
    def __init__(self, *args, **kwargs):
        super(StatsdLocust, self).__init__(*args, **kwargs)
        self.client = LocustStatsdClient(self.host, self.port)


class MetricGenerator(object):

    def __init__(self):
        self.metric_count = 0
    
    def get_metric(self):
        metric = "locust_client.%04d" % self.metric_count
        self.metric_count += 1
        return metric


class StatsdTest(StatsdLocust):
    
    host = "127.0.0.1"
    port = 8125
    min_wait = 10000
    max_wait = 10000
    metric_gen = MetricGenerator()

    def __init__(self, *args, **kwargs):
        super(StatsdTest, self).__init__(*args, **kwargs)
        self.metric = self.metric_gen.get_metric()
    
    class task_set(TaskSet):
        @task(1)
        def count(self):
            self.client.increment(self.locust.metric)

