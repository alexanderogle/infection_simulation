#!/usr/local/bin/python3
import random as r
import pandas as pd
import numpy as np
import copy
# Data structs for use in modeling infections

class Person():

    def __init__(self, id, state):
        self.id = id
        self.state = state
        self.infection_date = ""
        self.death_date = ""

    def update_state(self, new_state):
        self.state = new_state

    def get_id(self):
        return self.id

    def get_state(self):
        return self.state

    def infect(self, day):
        self.update_state("infected")
        self.infection_date= day

    def is_infected(self, day):
        self.infection_date = day

    def is_dead(self, day):
        self.death_date = day

    def get_infection_date(self):
        return self.infection_date

    def get_death_date(self):
        return self.death_date

    def __str__(self):
        return "Person object id: \"" + str(self.id) + "\" and state: \"" + str(self.state) + "\""


class Population():

    def __init__(self, id, population_size):
        self.people = {}
        if population_size > 0:
            for i in range(0, population_size):
                self.add_people(Person(i, "susceptible"))
        self.id = id

    def init_with_dict(self, people_dict):
        for i in range(0, len(people_dict)):
            self.add_people(people_dict[i])

    def add_people(self, person):
        self.people[person.get_id()] = person

    def update_person_state(self, id, state):
        self.people[id].update_state(state)

    def infect_person(self, id, day):
        self.people[id].infect(day)

    def get_population_size(self):
        return len(self.people)

    def get_population(self):
        """ Returns the people dict of this population object.
        The people dict should have the following format:

            people = {person_id_int_1: Person_object_1,
                      .
                      .
                      .
                      person_id_int_n: Person_object_n
                      }
        """
        return self.people

    def count_infected(self):
        infected = 0
        for person_id in self.people:
            if self.people[person_id].get_state() == "infected":
                infected += 1
        return infected

    def count_states(self, states):
        count = 0
        for person_id in self.people:
            for state in states:
                if self.people[person_id].get_state() == state:
                    count += 1
        return count

    def __str__(self):
        string = str(self.people)
        return string


class Network():
    """ Network class which constructs a network for a population.

    This class allows writing out and reading in of network files, which track
    change of state for connections between persons within a population, allowing
    for simulations of networks which are temporally variant.

    Once a Network object is initialized, its network can be accessed with the
    Network.get_network() method. This method returns the network dict which
    contains all the connection lists.
    """
    def __init__(self, population=""):
        if population:
            self.population = population
        self.network = {}
        for i in range(0, self.population.get_population_size()):
            self.network[i] = []

    def init_random_network(self, connection_min, connection_max, seed_num, verbose=False):
        r.seed(seed_num)
        pop = self.population.get_population()
        pop_size =len(pop)
        #TODO(aogle): Make it so that connections are 1:1 and still satisfy the
        #num_connections condition.
        num_connections = []
        for person_id in pop:
            num_connections.append(r.randint(connection_min, connection_max))

        completion_percent = 0
        for person_id in pop:
            connection_limit = num_connections[person_id]
            connections_list = self.network[person_id]
            for i in range(0, connection_limit):
                if len(connections_list) < connection_limit:
                    # Get a random person_id
                    connection_id = r.randint(0, pop_size-1)
                    other_person_connection_list = self.network[connection_id]
                    other_person_connection_limit = num_connections[connection_id]
                    # Ensure it isn't in the connections_list and the other
                    # person has space in their connections_list too.
                    while(connection_id in connections_list or len(other_person_connection_list) >= num_connections[connection_id]):
                        connection_id = r.randint(0, pop_size-1)
                        other_person_connection_list = self.network[connection_id]
                    # Add the random person_id to the connections_list
                    connections_list.append(connection_id)
                    completion_percent = (person_id / pop_size) * 100
                    if(verbose):
                        print("Generating random network: " + str(completion_percent) + "%")
            # Add the connections list to the network dict
            self.network[person_id] = connections_list

    def init_from_connections_dict(self, connections_dict):
        for person_id in connections_dict:
            self.network[person_id] = connections_dict[person_id]

    def from_csv(self, filepath):
        """Method for reading in a csv file of a network."""
        df = pd.read_csv(filepath).transpose()[:][1:]
        network = df.to_dict()
        # When we import, we have to convert the keys of the dicts in network to
        # ints, because they're imported as strings
        completion_percent = 0
        for key in network:
            connection_list = self.convert_str_key_to_int(network[key])
            network[key] = connection_list
            completion_percent = (key / len(network)) * 100
            print("Converting string keys to int keys: " + str(completion_percent) + "%")

        self.network = network

    def to_csv(self, filepath):
        """Method for exporting a network to a csv in the specified directory"""
        df = self.to_df()
        df.to_csv(filepath)

    def to_df(self):
        df = pd.DataFrame.from_dict(self.network, orient='index')
        return df

    # TODO(alexanderogle): move general utility functions to a separate file
    def convert_str_key_to_int(self, dict):
        x = {}
        for key in dict:
            new_key = int(key)
            x[new_key] = dict[key]
        return x

    def equals(self, other):
        df1 = self.to_df()
        df2 = self.to_df()
        return df1.equals(df2)

    def get_network(self):
        return self.network

    def get_population(self):
        return self.population

    def __str__(self):
        string = str(self.network)
        return string


class Policy():

    def __init__(self, id, max_days):
        self.id = id
        self.policy = {}
        self.policy_type = ""
        self.max_days = max_days

    def init_network_policy(self, connection_min, connection_max):
        self.policy_type = "linearly_interpolated_network"
        self.linearly_interpolated_network_policy(connection_min,
                                             connection_max, connection_min,
                                             connection_max)

    def linearly_interpolated_network_policy(self, connection_min_start,
                                     connection_max_start, connection_min_end,
                                     connection_max_end):
        """ Initiates a policy for a temporal network that linearly interpolates
        from connection_min/max_start to connection_min/max_end.
        TODO(aogle): find a method for better intepolation between min/max as
        the current method is crude.
        """
        self.policy_type = "lienarly_interpolated_network"
        connection_min_dict = {}
        connection_max_dict = {}

        x = [0, self.max_days]
        connect_min = [connection_min_start, connection_min_end]
        connect_max = [connection_max_start, connection_max_end]
        for day in range(0, self.max_days):
            connection_min = int(round(np.interp(day, x, connect_min)))
            connection_max = int(round(np.interp(day, x, connect_max)))

            # Checks that connection_max is never below connection_min
            if connection_max < connection_min:
                connection_max = connection_min

            connection_min_dict[day] = connection_min
            connection_max_dict[day] = connection_max

        self.policy["connection_min"] = connection_min_dict
        self.policy["connection_max"] = connection_max_dict

    def square_wave(self, connect_on, connect_off, frequency_on=1):
        """ connect_on is a list of two elements describing the [min, max]
        connections when social isolation is "in effect", connect_off is
        a list of two elements describing the [min, max] when the social
        isolation policy is lifted.

        A frequency_off of 1 represents social isolation not being in effect
        every day. frequency_off of 2 represents social isolation being in effect
        every other day, etc.
        """
        if frequency_on < 1:
            frequency_on = 1

        connection_min_dict = {}
        connection_max_dict = {}

        for day in range(0, self.max_days):
            policy_on = not(day%frequency_on)
            if policy_on:
                connection_min_dict[day] = connect_on[0]
                connection_max_dict[day] = connect_on[1]
            else:
                connection_min_dict[day] = connect_off[0]
                connection_max_dict[day] = connect_off[1]

        self.policy["connection_min"] = connection_min_dict
        self.policy["connection_max"] = connection_max_dict


    def edit_policy(self, days, connections_start, connections_end):
        start_day = days[0]
        end_day = days[1]
        connection_min_start = connections_start[0]
        connection_max_start = connections_start[1]
        connection_min_end = connections_end[0]
        connection_max_end = connections_end[1]
        x = [start_day, end_day]
        connect_min = [connection_min_start, connection_min_end]
        connect_max = [connection_max_start, connection_max_end]

        for day in range(start_day, end_day):
            connection_min = int(round(np.interp(day, x, connect_min)))
            connection_max = int(round(np.interp(day, x, connect_max)))

            if connection_max < connection_min:
                connection_max = connection_min

            self.policy["connection_min"][day] = connection_min
            self.policy["connection_max"][day] = connection_max

    def get_policy(self):
        return self.policy

    def policy_type(self):
        return self.policy_type

    def get_id():
        return self.id

    def __str__(self):
        string = "Policy type of \'" + self.policy_type + "\' with contents: \n"
        contents = ""
        for key in self.policy:
            contents += str(key) + " = " + str(self.policy[key]) + "\n"
        return string + contents


class TemporalNetwork():
    # TODO(alexanderogle): define a temporal network and its initialization,
    # export and import as csv, etc.
    def __init__(self, population, days):
        self.population = population
        self.days = days
        self.temporal_network = {}
        for day in range(0, self.days):
            self.temporal_network[day] = {}

    def init_random_network(self, connection_min, connection_max, seed_num, policy={}, verbose=False):
        # For each day, generate a random network to represent a randomly
        # evolving temporal network
        r.seed(seed_num)

        if policy:
            policy_dict = policy.get_policy()
            connection_min_dict = policy_dict["connection_min"]
            connection_max_dict = policy_dict["connection_max"]
        else:
            policy = Policy("static", self.days)
            policy.init_network_policy(connection_min, connection_max)
            policy_dict = policy.get_policy()
            connection_min_dict = policy_dict["connection_min"]
            connection_max_dict = policy_dict["connection_max"]

        completion_percent = 0
        for day in range(0, self.days):
            network_seed_num = r.randint(0,100000)
            network = Network(self.population)
            network.init_random_network(connection_min_dict[day],
                                        connection_max_dict[day],
                                        network_seed_num)
            self.temporal_network[day] = network
            if(verbose):
                completion_percent = (day / self.days) * 100
                print("Temporal Network Completion Percent: " + str(completion_percent))

    def get_network_dict(self, day):
        return self.temporal_network[day].get_network()

    def get_network(self, day):
        return self.temporal_network[day]

    def get_temporal_network(self):
        return self.temporal_network

    def get_population(self):
        return self.population


class Simulation():

    def __init__(self, population):
        self.population = population

    def seed_simulation(self, initial_infected, infection_probability,
                        recovery_period, recovery_probability, death_probability, seed_num):
        r.seed(seed_num)
        self.infection_probability = infection_probability
        self.recovery_period = recovery_period
        self.recovery_probability = recovery_probability
        self.death_probability = death_probability
        infected = 0
        pop = self.population.get_population()
        for person_id in pop:
            if infected < initial_infected:
                self.population.infect_person(person_id, 0)
                infected += 1

    def update(self, day):
        people = self.population.people
        for person_id in people:
            person = people[person_id]
            # Simulates probability of getting infection
            if r.random() < self.infection_probability and person.get_state() == "susceptible":
                person.update_state("infected")
                person.is_infected(day)
            # Simulates probability of dying
            if r.random() < self.death_probability and person.get_state() == "infected":
                person.update_state("dead")
                person.is_dead(day)
            # Simulates period it takes to recover
            if person.get_state() == "infected" and day - person.get_infection_date() > self.recovery_period:
                person.update_state("recovered")


    def get_snapshot(self):
        return self.population

    def simulate(self, max_days, verbose=True):
        timeline = {0: self.get_snapshot()}
        infection_timeline = {0: self.population.count_infected()}
        not_infected_states = ["susceptible", "recovered"]
        not_infected_timeline = {0: self.population.count_states(not_infected_states)}
        alive_states = ["susceptible", "infected", "recovered"]
        alive_timeline = {0: self.population.count_states(alive_states)}

        completion_percent = 0
        for day in range(1, max_days):
            self.update(day)
            timeline[day] = self.get_snapshot()
            infection_timeline[day] = self.population.count_infected()
            not_infected_timeline[day] = self.population.count_states(not_infected_states)
            alive_timeline[day] = self.population.count_states(alive_states)

            if verbose:
                completion_percent = (day/max_days)*100
                print("Percent Simulation Complete: " + str(completion_percent) + "%")
        return timeline, infection_timeline, not_infected_timeline, alive_timeline

    def __str__(self):
        string = str(self.population)
        return string


class NetworkSimulation(Simulation):
    """ Simulates propogation of an infection through a static network in a population.
    """
    def __init__(self, network):
        self.population = network.get_population()
        self.network = network

    def get_snapshot(self):
        return self.population, self.network

    def update(self, day):
        people = self.population.people
        for person_id in people:
            person = people[person_id]
            # Only use infected individuals' connections for updating infection status
            # Simulates probability of individuals connected to infected individual
            # getting infected.
            network = self.network.get_network()
            connections_list = network[person_id]
            if person.get_state() == "infected":
                for connection in connections_list:
                    connected_person = people[connection]
                    if r.random() < self.infection_probability and connected_person.get_state() == "susceptible":
                        connected_person.update_state("infected")
                        connected_person.is_infected(day)
            # Simulates probability of dying
            if r.random() < self.death_probability and person.get_state() == "infected":
                person.update_state("dead")
                person.is_dead(day)
            # Simulates period it takes to recover and probability of recovering
            if person.get_state() == "infected" and day - person.get_infection_date() > self.recovery_period and r.random() < self.recovery_probability:
                person.update_state("recovered")

    def simulate(self, max_days, verbose=True):
        initial_population, initial_network = self.get_snapshot()
        timeline = {0: {"population": initial_population, "network": initial_network}}
        infection_timeline = {0: self.population.count_infected()}
        susceptible_timeline = {0: self.population.count_states(["susceptible"])}
        recovered_timeline = {0: self.population.count_states(["recovered"])}
        dead_timeline = {0: self.population.count_states(["dead"])}

        completion_percent = 0
        for day in range(1, max_days):
            self.update(day)
            population, network = self.get_snapshot()
            timeline[day] = {"population": population, "network": network}
            infection_timeline[day] = population.count_infected()
            susceptible_timeline[day] = population.count_states(["susceptible"])
            recovered_timeline[day] = population.count_states(["recovered"])
            dead_timeline[day] = population.count_states(["dead"])

            if verbose:
                completion_percent = (day/max_days)*100
                print("Percent Simulation Complete: " + str(completion_percent) + "%")
        return timeline, infection_timeline, susceptible_timeline, recovered_timeline, dead_timeline


class TemporalNetworkSimulation(NetworkSimulation):
    # TODO(alexanderogle): Will update class methods here after creating the
    # TemporalNetwork object
    def __init__(self, temporal_network):
        self.population = temporal_network.population
        self.temporal_network = temporal_network

    def get_snapshot(self, day):
        return self.population, self.temporal_network.get_network(day)

    def update(self, day):
        people = self.population.people
        for person_id in people:
            person = people[person_id]
            # Only use infected individuals' connections for updating infection status
            # Simulates probability of individuals connected to infected individual
            # getting infected.
            network = self.temporal_network.get_network_dict(day)
            connections_list = network[person_id]
            if person.get_state() == "infected":
                for connection in connections_list:
                    connected_person = people[connection]
                    if r.random() < self.infection_probability and connected_person.get_state() == "susceptible":
                        connected_person.update_state("infected")
                        connected_person.is_infected(day)
            # Simulates probability of dying
            if r.random() < self.death_probability and person.get_state() == "infected":
                person.update_state("dead")
                person.is_dead(day)
            # Simulates period it takes to recover and probability of recovering
            if person.get_state() == "infected" and day - person.get_infection_date() > self.recovery_period and r.random() < self.recovery_probability:
                person.update_state("recovered")

    def simulate(self, max_days, verbose=True):
        initial_population, initial_network = self.get_snapshot(0)
        timeline = {0: {"population": copy.deepcopy(initial_population), "network": initial_network}}
        infection_timeline = {0: self.population.count_infected()}
        susceptible_timeline = {0: self.population.count_states(["susceptible"])}
        recovered_timeline = {0: self.population.count_states(["recovered"])}
        dead_timeline = {0: self.population.count_states(["dead"])}

        completion_percent = 0
        for day in range(1, max_days):
            self.update(day)
            population, network = self.get_snapshot(day)
            timeline[day] = {"population": copy.deepcopy(population), "network": network}
            infection_timeline[day] = self.population.count_infected()
            susceptible_timeline[day] = self.population.count_states(["susceptible"])
            recovered_timeline[day] = self.population.count_states(["recovered"])
            dead_timeline[day] = self.population.count_states(["dead"])

            if verbose:
                completion_percent = (day/max_days)*100
                print("Percent Simulation Complete: " + str(completion_percent) + "%")
        return timeline
