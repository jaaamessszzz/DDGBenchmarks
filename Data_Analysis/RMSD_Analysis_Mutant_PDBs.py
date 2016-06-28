import pandas as pd
import sys
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import pickle
import re

def dataframe_construction(StructuralMetrics_pickle):
    mutant_df = pd.DataFrame(columns=('Prediction ID', 'WT PDBID', 'Mutant PDBID', 'RMSD Type', 'Point Mutant', 'RMSD', 'Predicted DDG', 'Experimental DDG', 'Absolute Error DDG', 'PDBID : Point Mutant'))
    PDB_set = set()
    tossed_set = set()
    PredID_set = set()
    mutant_set = set()

    def add_to_df(PredictionID, Mutant_PDB, rmsd_type, point_mutant, rmsd_value, mutant_df):
        temp_df = pd.DataFrame(columns=('Prediction ID', 'WT PDBID', 'Mutant PDBID', 'RMSD Type', 'Point Mutant', 'RMSD', 'PDBID : Point Mutant'))
        temp_df.loc[Mutant_PDB.split()[0]] = pd.Series({'Prediction ID': PredictionID,
                                                        'WT PDBID': Mutant_PDB.split()[0],
                                                        'Mutant PDBID': Mutant_PDB,
                                                        'PDBID : Point Mutant': '%s %s' %(Mutant_PDB, point_mutant),
                                                        'RMSD Type': rmsd_type[:-5],
                                                        'RMSD': rmsd_value,
                                                        'Point Mutant': Mutant_PDB
                                                        }
                                                       )
        mutant_df = pd.concat([mutant_df, temp_df])
        return mutant_df

    with open('/kortemmelab/home/james.lucas/DDGBenchmarks_Test/Data_Analysis/RMSD_Outfiles/%s' %StructuralMetrics_pickle, 'rb') as input:
        RMSD_dict = pickle.load(input)

    Dataframe_pickle = '%s%s' % ('Dataframe-', StructuralMetrics_pickle[18:])

    try:
        with open('/kortemmelab/home/james.lucas/DDGBenchmarks_Test/Data_Analysis/RMSD_Outfiles/%s' % Dataframe_pickle, 'rb') as input:
            mutant_df = pickle.load(input)

        for PredictionID in RMSD_dict:
            PredID_set.add(PredictionID)
            for nested_PredID in RMSD_dict[PredictionID]:
                for Mutant_PDB in RMSD_dict[PredictionID][nested_PredID]:
                    if RMSD_dict[PredictionID][nested_PredID][Mutant_PDB]['Global RMSD']['Mean'] > 10:
                        tossed_set.add(Mutant_PDB)
                    else:
                        PDB_set.add(Mutant_PDB)
                        for rmsd_type in RMSD_dict[PredictionID][PredictionID][Mutant_PDB]:
                            if type(RMSD_dict[PredictionID][PredictionID][Mutant_PDB][rmsd_type]) == list:  # rmsd[0] = Point Mutant Position, rmsd[1] = Dict
                                for point_mutant in RMSD_dict[PredictionID][PredictionID][Mutant_PDB][rmsd_type]:
                                    mutant_set.add('%s %s' % (Mutant_PDB, point_mutant[0]))
    except:
        for PredictionID in RMSD_dict:
            PredID_set.add(PredictionID)
            for Mutant_PDB in RMSD_dict[PredictionID][PredictionID]:
                if RMSD_dict[PredictionID][PredictionID][Mutant_PDB]['Global RMSD']['Mean'] > 10:
                    tossed_set.add(Mutant_PDB)
                else:
                    PDB_set.add(Mutant_PDB)
                    for rmsd_type in RMSD_dict[PredictionID][PredictionID][Mutant_PDB]:
                        if type(RMSD_dict[PredictionID][PredictionID][Mutant_PDB][rmsd_type]) == list: # rmsd[0] = Point Mutant Position, rmsd[1] = Dict
                            for point_mutant in RMSD_dict[PredictionID][PredictionID][Mutant_PDB][rmsd_type]:
                                mutant_set.add('%s %s' %(Mutant_PDB, point_mutant[0]))
                                for rmsd_value in point_mutant[1]['Raw']:
                                    mutant_df = add_to_df(PredictionID, Mutant_PDB, 'Point Mutant', point_mutant[0], rmsd_value, mutant_df)
                        else:
                            for rmsd_value in RMSD_dict[PredictionID][PredictionID][Mutant_PDB][rmsd_type]['Raw']:
                                mutant_df = add_to_df(PredictionID, Mutant_PDB, rmsd_type, None, rmsd_value, mutant_df)

        with open('/kortemmelab/home/james.lucas/DDGBenchmarks_Test/Data_Analysis/RMSD_Outfiles/%s' % Dataframe_pickle, 'wb') as output:
            pickle.dump(mutant_df, output, 0)

    mutant_df = mutant_df.reset_index(drop = True)

    return RMSD_dict, mutant_df, PDB_set, tossed_set, PredID_set, mutant_set

def apply_settings(fig, ax):
    handles, labels = ax.get_legend_handles_labels()
    ldg = ax.legend(handles, labels, loc='center left', bbox_to_anchor=(1, 0.5))
    sns.set_style('white', {'axes.grid': True})
    sns.set_context('notebook', font_scale=1, rc={'lines.linewidth': 1})
    sns.despine()
    title = fig.suptitle('Average RMSD of Rosetta-Generated Ensemble Against a Reference Mutant Crystal Structure', wrap=True, fontsize = 32)
    return fig, ax

def plot_stuff(mutant_df, PDB_set, tossed_set, PredID_set, mutant_set):
    # Import dataframes
    data_df = pd.read_csv('/kortemmelab/home/kyleb/reports/160608/analysis_sets/ZEMu/ddg_analysis_type_CplxBoltzWT16.0-prediction_set_id_zemu-brub_1.6-nt10000-score_method_Rescore-Talaris2014/data.csv')
    skempi_df = pd.read_csv('/kortemmelab/home/james.lucas/skempi_mutants.tsv', delimiter='\t')

    # Modify mutant_df to include Predicted DDG values
    try:
        with open('mutant_df_DDGs_cached.pickle', 'rb') as input:
            mutant_df = pickle.load(input)

    except:
        for skempi_index, skempi_row in skempi_df.iterrows():
            # Format mutation string
            split_mutation = re.sub(':|-|>', ' ', skempi_row['Mutations']).split(',')
            temp_string_list = []
            for mutation in split_mutation:
                letters = mutation.split()
                temp_string_list.append('%s %s %s %s' %(letters[0], letters[1], ('   ' + letters[2])[-3:], letters[3]))
            joinme = '; '
            formatted_mutation = joinme.join(temp_string_list)

            # Iterate through data_df to find correct DDG values
            for data_index, data_row in data_df.iterrows():
                if formatted_mutation == data_row['Mutations'] and skempi_row['Wildtype'] == data_row['PDBFileID'] and (skempi_row['Wildtype'] + ' : ' + skempi_row['Mutant']) not in tossed_set:
                    # Add DDG values to mutant_df
                    print (skempi_row['Wildtype'] + ' : ' + skempi_row['Mutant'])
                    for mutant_index, mutant_row in mutant_df.iterrows():
                        if (skempi_row['Wildtype'] + ' : ' + skempi_row['Mutant']) == mutant_row['Mutant PDBID']:
                            mutant_df.loc[mutant_index, 'Predicted DDG'] = data_row['Predicted']/1.2 # Scaling factor suggested by Shane
                            mutant_df.loc[mutant_index, 'Experimental DDG'] = data_row['Experimental_ZEMu']
                            mutant_df.loc[mutant_index, 'Absolute Error DDG'] = abs(data_row['Experimental_ZEMu'] - data_row['Predicted'])
                    break

        with open('mutant_df_DDGs_cached.pickle', 'wb') as output:
            pickle.dump(mutant_df, output, 0)

    for type, df_subset in mutant_df.groupby('RMSD Type'):
        if type != 'Point M':
            # Scatter plot
            fig, ax = plt.subplots(figsize=(10, 10))
            ax = sns.regplot('Absolute Error DDG', 'RMSD', data=df_subset, x_estimator=np.mean, fit_reg=False)
            ax.set_xlabel('DDG Absolute Error', fontsize=16)
            ax.set_ylabel('Average RMSD', fontsize=16)
            ax.set_xlim(0,6)
            ax.set_ylim(0,2)
            ax = apply_settings(fig, ax)

            plt.show()

            ax = sns.boxplot(x='RMSD',y='Mutant PDBID',order=sorted(list(PDB_set)),data=df_subset)
            plt.show()
        else:
            # Scatter plot
            fig, ax = plt.subplots(figsize=(10, 10))
            ax = sns.lmplot('Absolute Error DDG', 'RMSD', hue='PDBID : Point Mutant',data=df_subset, x_estimator=np.mean, fit_reg=False, legend=False)
            plt.show()
            # Boxplot
            fig, ax = plt.subplots(figsize=(20, 10))
            ax = sns.boxplot(x='RMSD', y='PDBID : Point Mutant', order=sorted(list(mutant_set)) , data=df_subset)
            sns.set_context('notebook', font_scale=0.5, rc={'lines.linewidth': 1})
            plt.show()
    sys.exit()

    # fig.savefig("%s_boxplot_test.pdf" %type,)


def main():
    StructuralMetrics_pickle = 'StructuralMetrics-ddg_analysis_type_CplxBoltzWT16.0-prediction_set_id_zemu-brub_1.6-nt10000-score_method_Rescore-Talaris2014.pickle'
    RMSD_dict, mutant_df, PDB_set, tossed_set, PredID_set, mutant_set = dataframe_construction(StructuralMetrics_pickle)
    plot_stuff(mutant_df, PDB_set, tossed_set, PredID_set, mutant_set)

main()