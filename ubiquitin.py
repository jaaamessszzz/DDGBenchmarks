import sys
sys.path.insert(0, "..")


from klab import colortext
from klab.bio.pdb import PDB
from klab.bio.basics import Mutation, ChainMutation, generate_all_combinations_of_mutations
from klab.fs.fsio import read_file, write_file

from ddglib import ddgdbapi, dbapi

if __name__ == '__main__':
    DDGdb = ddgdbapi.ddGDatabase()
    ddG_connection = dbapi.ddG()

all_wildtype_mutations = '''
# All mutations are on chain A
A83P, I86L, S87A
L95I, I98V
A83P, I86L, S87A, L95I, I98V
'''


ubiquitin_chains = [
    #('ub_SH3', 'A', 'Ubiquitin scan: SH3 p16'),
    #('1ubq', 'A', 'Ubiquitin scan: 1UBQ p16'),
    #('ub_CUE', 'A', 'Ubiquitin scan: CUE p16'),
    #('ub_OTU', 'A', 'Ubiquitin scan: OTU p16'),
    #('ub_RPN13', 'A', 'Ubiquitin scan: RPN13 p16'),
    #('ub_UQcon', 'A', 'Ubiquitin scan: UQ_con p16'),
    #('uby_1UBQ', 'A', 'Ubiquitin scan: 1UBQ_yeast p16'),
    #('uby_OTU', 'A', 'Ubiquitin scan: OTU_yeast p16'),
    #('uby_RPN13', 'A', 'Ubiquitin scan: RPN13_yeast p16'),
    #('uby_SH3', 'A', 'Ubiquitin scan: SH3_yeast p16'),
    #('uby_UQcon', 'A', 'Ubiquitin scan: UQ_con_yeast p16'),
    ('uby_CUE', 'A', 'Ubiquitin scan: CUE_yeast p16'),
]

if False:

    # I have (hopefully) written these functions so that they can be run multiple times without consequences e.g.
    #  - if you accidentally add the same mutation string a second time, it will be handled gracefully;
    #  - if you run add_predictions_by_pdb_id multiple times, it won't force jobs to be re-run.

    # Here is an example usage:

    ### Computational stage ###

    # Step 1: Add a new PDB
    ddG_connection.add_PDB_to_database('/kortemmelab/home/oconchus/ubiquitin/CUE.pdb', 'ub_CUE', file_source = 'Biosensor project', techniques = 'Rosetta model')
    ddG_connection.add_PDB_to_database('/kortemmelab/home/oconchus/ubiquitin/OTU.pdb', 'ub_OTU', file_source = 'Biosensor project', techniques = 'Rosetta model')
    ddG_connection.add_PDB_to_database('/kortemmelab/home/oconchus/ubiquitin/RPN13.pdb', 'ub_RPN13', file_source = 'Biosensor project', techniques = 'Rosetta model')
    ddG_connection.add_PDB_to_database('/kortemmelab/home/oconchus/ubiquitin/SH3.pdb', 'ub_SH3', file_source = 'Biosensor project', techniques = 'Rosetta model')
    ddG_connection.add_PDB_to_database('/kortemmelab/home/oconchus/ubiquitin/UQ_con.pdb', 'ub_UQcon', file_source = 'Biosensor project', techniques = 'Rosetta model')

    ddG_connection.add_PDB_to_database('/kortemmelab/home/oconchus/ubiquitin/1UBQ_yeast.pdb', 'uby_1UBQ', file_source = 'Biosensor project', techniques = 'Rosetta model')
    ddG_connection.add_PDB_to_database('/kortemmelab/home/oconchus/ubiquitin/OTU_yeast.pdb', 'uby_OTU', file_source = 'Biosensor project', techniques = 'Rosetta model')
    ddG_connection.add_PDB_to_database('/kortemmelab/home/oconchus/ubiquitin/RPN13_yeast.pdb', 'uby_RPN13', file_source = 'Biosensor project', techniques = 'Rosetta model')
    ddG_connection.add_PDB_to_database('/kortemmelab/home/oconchus/ubiquitin/SH3_yeast.pdb', 'uby_SH3', file_source = 'Biosensor project', techniques = 'Rosetta model')
    ddG_connection.add_PDB_to_database('/kortemmelab/home/oconchus/ubiquitin/UQ_con_yeast.pdb', 'uby_UQcon', file_source = 'Biosensor project', techniques = 'Rosetta model')
    ddG_connection.add_PDB_to_database('/kortemmelab/home/oconchus/ubiquitin/CUE_yeast.pdb', 'uby_CUE', file_source = 'Biosensor project', techniques = 'Rosetta model')

    # Step 2: Add a list of mutations for each PDB
    #
    # generate_all_point_mutations generates all possible point mutations for the specified chain.

    ubq_sequence = 'MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRG'
    for uc in ubiquitin_chains:
        # Generate a list of all possible mutations for the ubiquitin chains
        pdb_id = uc[0]
        chain_id = uc[1]
        p = PDB(ddG_connection.ddGDB.execute_select('SELECT Content FROM PDBFile WHERE ID=%s', parameters=(pdb_id,))[0]['Content'])
        #print('\n'.join(p.lines))
        assert(str(p.atom_sequences[chain_id]).find('MQIFV') != -1) and (str(p.atom_sequences[chain_id]).find('HLVLRLRG') != -1)
        mutant_list = p.generate_all_point_mutations_for_chain(chain_id)
        colortext.message('Generated %d mutations for %s.' % (len(mutant_list), pdb_id))
        colortext.warning('Adding mutants...')
        count = 0
        for mutant_mutation in mutant_list:
            ddG_connection.add_mutant(pdb_id, [mutant_mutation])
            if count % 20 == 0:
                sys.stdout.write('.')
            count += 1
        sys.stdout.write('\n')

if False:

    import pickle
    results = ddG_connection.ddGDB.execute_select('SELECT ID, PredictionSet, InputFiles FROM Prediction WHERE PredictionSet LIKE "Ubiquitin scan%%"', parameters=())
    for r in results:
        mutfile = pickle.loads(r['InputFiles'])['MUTFILE']
        if mutfile.find('total 1') == -1:
            print(mutfile)
            print('DELETE FROM Prediction WHERE ID=%s' %(r['ID']))
            #results = ddG_connection.ddGDB.execute('DELETE FROM Prediction WHERE ID=%s', parameters=(r['ID']))
            sys.exit(0)

if True:
    # Step 3:
    # This function will queue any mutations which have not previously run on the cluster or which are not in the queue.
    # The second parameter is a 'prediction set'. This is just a label used to group a set of predictions together. It makes sense
    # to group all predictions using the same protocol together.
    # The third parameter is the name of the DDG protocol. All protocols currently in the database are variants of protocol 16
    # from the Kellogg, Leaver-Fay, Baker paper (doi:10.1002/prot.22921).

    priority = 9 + len(ubiquitin_chains)
    count = 0
    for uc in ubiquitin_chains:
        priority -= 1 # assign different priorities to the different prediction sets
        ddG_connection.add_predictions_by_pdb_id(uc[0], uc[2], 'Protocol16 3.5.1 (talaris2013sc)', status = 'halted', priority = priority, KeepHETATMLines = False, strip_other_chains = False)
        count += 1
        #if count == 2:
        #    sys.exit(1)

if False:
    # Steps 2 and 3 can be repeated as often as you need however it is best to add as many mutations in step 2 first as this
    # will result in a better use of the cluster (larger array jobs).

    ### Analysis stage ###

    # To see the results quickly, you can use the get_flattened_prediction_results function e.g.
    colortext.message('Retrieving results')
    ddG_connection.get_flattened_prediction_results('FPP biosensor: protocol 16')

    # The create_abacus_graph_for_a_single_structure function will create a sorted graph of the results showing which sets of mutations are predicted to be more stable
    colortext.message('Analyzing results')
    ddG_connection.create_abacus_graph_for_a_single_structure('FPP biosensor: protocol 16', 'kellogg', 'total', graph_filename = 'L87Y_removed.png')

    # This is a simple test function which prints out the sequences of the monomer wildtype sequence and mutant sequence,
    # highlighting where they differ in case there was a mistake in the pipeline.
    # First, the output files are downloaded and extracted to the directory specified in the first argument.
    colortext.message('Testing results')
    ddG_connection.test_results('random_output_data', 'FPP biosensor: protocol 16')

    # This function creates a PyMOL session
    # The output files are downloaded and extracted to the directory specified in the second argument.
    # This function takes in a Prediction ID. These can be retrieved using the get_flattened_prediction_results function above.
    # The fourth argument is a task ID e.g. Protocol 16 generates 50 pairs of wildtype and mutant models by default, numbered
    # 1 to 50. This argument picks one of those pairs and creates a PyMOL session with aligned structures and with the mutations
    # highlighted.
    colortext.message('Creating PyMOL session')
    ddG_connection.create_pymol_session('test.pse', 'random_output_data', 53858, 25)

