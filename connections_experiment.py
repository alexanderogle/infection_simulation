import pandas as pd
import numpy as np
import time
import sys
import resource
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import pickle as pkl
sys.setrecursionlimit(10**6)


class MemoryMonitor:
    def __init__(self):
        self.keep_measuring = True

    def measure_usage(self):
        max_usage = 0
        usage = []
        while self.keep_measuring:
            max_usage = max(
                max_usage,
                resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            )

            time.sleep(0.1)

        return max_usage


class ConnectionEngine():
    def __init__(self, num_people=None, num_connections=None):
        self.num_people = num_people
        self.num_connections = num_connections

    def _build_connection_list(self, agent, population, num_connections):
        # Break ounter
        # if _cnt == 0:
        #    _cnt += 1
        # Return IDs of people with connections less than num_connections
        available_to_connect = (
            lambda agent, population: population.drop(agent).query('num_connections < {}'
                                                                   .format(num_connections)
                                                                   ).index
        )

        # Update number of connections
        #population['num_connections'] = population.connections.apply(len)
        # Get other agents available to connect
        available = available_to_connect(agent, population)
        # Randomly choose connection
        if len(available) > 0:
            connection = np.random.choice(available)
            # Make connection
            population.iloc[connection].connections.append(agent)
            population.iloc[agent].connections.append(connection)

            # Update number of connections
            population.iloc[[agent, connection], 2] += 1
            # if _cnt < 10:
            while population.num_connections[agent] < num_connections:
                self._build_connection_list(agent,
                                            population,
                                            num_connections)

        return population

    def create_connections(self, verbose=False):
        num_connections = self.num_connections
        num_people = self.num_people
        population = pd.DataFrame(
            {
                'index': [i for i in range(num_people)],
                'connections': [[] for i in range(num_people)],
                'num_connections': [0 for i in range(num_people)]
            }
        )

        _update = num_people*0.1
        for _per in population.index:
            if verbose:
                if _per % _update == 0:
                    print('{:.0f}% complete'.format(_per/num_people*100))
            self._build_connection_list(_per, population, num_connections)

        self.population = population

        return population


class ConnectionsExperiment():
    def __init__(self, num_people=None, num_connections=None, connection_engine=None, num_runs=1):
        self.num_people = num_people
        self.num_connections = num_connections
        self.connection_engine = connection_engine
        self.num_runs = num_runs
        self.data = []

    def single_experiment(self, num_connections=None, num_people=None):
        if num_connections is None:
            num_connections = self.num_connections
        if num_people is None:
            num_people = self.num_people
        start = time.time()
        xns = self.connection_engine(num_people=num_people, num_connections=num_connections)
        xns.create_connections()
        del xns
        end = time.time()
        output = {
            'num_people': num_people,
            'num_connections': num_connections,
            'time': end-start
        }
        self.data.append(output)

    def run(self):
        # Overall runtime tracking
        start = time.time()
        # Set variables
        num_people = self.num_people
        num_connections = self.num_connections
        num_runs = self.num_runs

        # Allows handling of single values
        if isinstance(num_people, int):
            num_people = [num_people]
        if isinstance(num_connections, int):
            num_connections = [num_connections]
        # if isinstance(num_runs,int):
        #    num_runs = [num_runs]

        # Main
        for run in range(num_runs):
            for _np in num_people:
                for _nc in num_connections:
                    try:
                        # TODO: Abstract out the Thread Pool Memory Monitor
                        with ThreadPoolExecutor() as executor:
                            monitor = MemoryMonitor()
                            mem_thread = executor.submit(monitor.measure_usage)
                            try:
                                fn_thread = executor.submit(
                                    experiment.single_experiment(
                                        num_people=_np, num_connections=_nc)
                                )
                            finally:
                                monitor.keep_measuring = False
                                max_usage = mem_thread.result()

                            # Log Max Memory Usage
                            self.data[-1]['max_memory'] = max_usage

                    except:
                        # Bad run
                        output = {
                            'num_people': num_people,
                            'num_connections': num_connections,
                            'time': None,
                            'max_memory': None
                        }
                        self.data.append(output)

        # Overall runtime tracking
        end = time.time()
        self.runtime = end - start
        return self.data


if __name__ == '__main__':
    #num_people = [100, 500, 1000, 5000, 10000]
    #num_connections = [5, 10, 15, 20, 25, 30]

    #experiment = ConnectionsExperiment(num_people=num_people, num_connections=num_connections)
    experiment = ConnectionsExperiment(
        num_people=100,
        num_connections=[5, 6, 7],
        connection_engine=ConnectionEngine,
        num_runs=3
    )

    experiment.run()
    print(experiment.data)

    with open('connections_experiment_results_{}.pkl'.format(int(time.time())), 'wb') as file_:
        pkl.dump(experiment, file_)
