import random
import sys
import subprocess
from threading import Thread
from pickle import load
from pickle import dump
from deap import base
from deap import creator
from deap import tools

# http://deap.readthedocs.io/en/master/api/creator.html
# Creator is a meta-factory that creates classes
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax, min=0, max=0, std_dev=0)

# Constants
NUMBER_OF_WEIGHTS = 22
MUTATION_GENE_RATE = 0.05
MUTATION_GENE_INDIVIDUAL_RATE = 0.2
CROSSOVER_RATE = 0.5
GENERATION_COUNT = 100
POPULATION_SIZE = 50
FITNESS_FUNCTION_AVERAGE_COUNT = 3
LAST_GENERATION_FILE_NAME = "last_gen.pickle"

class GeneticAlgorithmRunner:
    def __init__(self):
        self._init_toolbox()

    # Change the genetic algorithm here for optimisation    
    def _init_toolbox(self):
        self._toolbox = base.Toolbox()
        # define 'attr_bool' to be an attribute ('gene') which corresponds to integers sampled uniformly from the range [0,1]
        self._toolbox.register("attr_float", random.random)
        self._toolbox.register("individual", tools.initRepeat, creator.Individual, self._toolbox.attr_float, NUMBER_OF_WEIGHTS)
        # define the population to be a list of individuals
        self._toolbox.register("population", tools.initRepeat, list, self._toolbox.individual)
        # register the goal / fitness function
        self._toolbox.register("evaluate", self.fitness_function)
        # register the crossover operator
        self._toolbox.register("mate", tools.cxOnePoint)
        # register a mutation operator with a probability to flip each attribute/gene with probability
        self._toolbox.register("mutate", tools.mutUniformInt, indpb=MUTATION_GENE_RATE, low=0, up=1)
        self._toolbox.register("select", tools.selTournament, tournsize=5)

    def init_population(self):
        return self._toolbox.population(n=POPULATION_SIZE)
    
    # Given a population, calculate fitness for every single individual
    def evaluate_population(self, pop):
        fitness_stats = list(self.map_evaluate(pop))
        for ind, fit in zip(pop, fitness_stats):
            ind.fitness.values = fit[0]
            ind.min = fit[1]
            ind.max = fit[2]
            ind.std_dev = fit[3]
        return pop

    def map_evaluate(self, pop):
        results = [None] * len(pop)
        threads = [None] * len(pop)
        for i in range(len(threads)):
            threads[i] = Thread(target=self.map_fitness_function, args=(pop[i], results, i))
            threads[i].start()

        for i in range(len(threads)):
            threads[i].join()
        return results

    def map_fitness_function(self, individual, results, i):
        results[i] = self.fitness_function(individual)

    def mutate(self, pop):
        for mutant in pop:
            if random.random() < MUTATION_GENE_INDIVIDUAL_RATE:
                self._toolbox.mutate(mutant)
                del mutant.fitness.values
        return pop

    def crossover(self, pop):
        for child1, child2 in zip(pop[::2], pop[1::2]):
            # cross two individuals with probability CXPB
            if random.random() < CROSSOVER_RATE:
                self._toolbox.mate(child1, child2)

                # fitness values of the children
                # must be recalculated later
                del child1.fitness.values
                del child2.fitness.values

    def run(self, pop):
        for i in range(GENERATION_COUNT):
            print("-- Generation "+ str(i+1) + "--")
            # Select the next generation individuals
            offspring = self._toolbox.select(pop, len(pop))
            offspring = list(map(self._toolbox.clone, offspring))
            self.crossover(offspring)
            offspring = self.mutate(offspring)
            # Evaluate the crossovers and mutated individuals
            invalid_ind = self.evaluate_population([ind for ind in offspring if not ind.fitness.valid])
            print("  Evaluated %i individuals" % len(invalid_ind))
            # The population is entirely replaced by the offspring
            pop[:] = offspring
            self.report_current_generation(pop)
            # Remove all calculated, since the game has high standard deviation
            # This is to prevent some individuals prevails on one-shot high score
            if i != GENERATION_COUNT - 1:
                for ind in pop:
                    del pop.fitness.values
        return pop

    # Change this function to alter the generation reporting
    def report_current_generation(self, pop):
        # Gather all the fitnesses in one list and print the stats
        fits = [ind.fitness.values[0] for ind in pop]
        length = len(pop)
        mean = sum(fits) / length
        sum2 = sum(x*x for x in fits)
        std = abs(sum2 / length - mean**2)**0.5
        
        print("  Min %s" % min(fits))
        print("  Max %s" % max(fits))
        print("  Avg %s" % mean)
        print("  Std %s" % std)
        best_ind = tools.selBest(pop, 1)[0]
        print("  Best individual is %s" %(best_ind))

    # Saves the generation into disk using pickle
    def saves_gen_into_disk(self, pop, file_name):
        dump(pop, open(file_name, "wb"))

    def thread_fitness_function(self, individual, results, i):
        results[i] = int(subprocess.check_output(['java', '-classpath', "out/", "NoVisualPlayerSkeleton"]).strip())
    
    # Given an individual, calculate its fitness value
    def fitness_function(self, individual):
        result = []
        threads = [None] * FITNESS_FUNCTION_AVERAGE_COUNT
        results = [None] * FITNESS_FUNCTION_AVERAGE_COUNT
        for i in range(len(threads)):
            threads[i] = Thread(target=self.thread_fitness_function, args=(individual, results, i))
            threads[i].start()

        for i in range(len(threads)):
            threads[i].join()
        mean = reduce(lambda x, y: x + y, results) / len(results)
        sum2 = sum(x*x for x in results)
        std = abs(sum2 / len(results) - mean**2)**0.5
        return ((mean,),min(results), max(results), std)

def set_random_seed():
    random.seed(64)

def main():
    set_random_seed()
    genetic_algo = GeneticAlgorithmRunner()
    pop = genetic_algo.init_population()
    
    print("Start of evolution")
    
    # Evaluate the entire population
    pop = genetic_algo.evaluate_population(pop)

    # Run the genetic algorithm and returns the last generation
    pop = genetic_algo.run(pop)
    genetic_algo.saves_gen_into_disk(pop, LAST_GENERATION_FILE_NAME)

if __name__ == "__main__":
    try:
        main()
    except:
        print("Error found", sys.exc_info()[0])
        sys.exit()