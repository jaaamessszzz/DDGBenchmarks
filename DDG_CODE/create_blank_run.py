import os, sys
import shutil
import pprint
import json

# Add parent directory to path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ddglib.ppi_api import get_interface_with_config_file
import klab.cluster_template.parse_settings as parse_settings
import time
import getpass
import json
import re
import shutil
import importlib
from klab.cluster_template.write_run_file import process as write_run_file
from klab import colortext
from klab.fs.fsio import write_file
import cPickle as pickle

job_output_directory = 'job_output'


if __name__ == '__main__':
    assert( len(sys.argv) > 1 )
    cfg = importlib.import_module(sys.argv[1], package=None)

    prediction_set_id = cfg.prediction_set_id

    suppress_warnings = True

    # This uses the version of Rosetta from your cluster template settings file
    settings = parse_settings.get_dict()
    rosetta_scripts_path = settings['local_rosetta_installation_path'] + '/source/bin/' + 'rosetta_scripts' + settings['local_rosetta_binary_type']
    ppi_api = get_interface_with_config_file(rosetta_scripts_path = rosetta_scripts_path, rosetta_database_path = '/home/kyleb/rosetta/working_branches/alascan/database')

    # Read the keep_hetatm_lines optional setting
    keep_hetatm_lines = False
    keep_all_lines = False
    try: keep_hetatm_lines = cfg.keep_hetatm_lines
    except: colortext.warning('Note: keep_hetatm_lines is not specified in {0}. Defaulting to {1}.'.format(sys.argv[1], keep_hetatm_lines))
    try: keep_all_lines = cfg.keep_all_lines
    except: colortext.warning('Note: keep_all_lines is not specified in {0}. Defaulting to {1}.'.format(sys.argv[1], keep_all_lines))

    t1, t2 = None, None
    if not ppi_api.prediction_set_exists(prediction_set_id):
        print 'Creating new prediction set:', prediction_set_id
        t1 = time.time()
        ppi_api.add_prediction_set(prediction_set_id, halted = True, priority = 7, allow_existing_prediction_set = False, description = cfg.prediction_set_description)

        # Populate the prediction set with jobs from a (tagged subset of a) user dataset
        print 'Created PredictionSet:', prediction_set_id
        ppi_api.add_prediction_run(prediction_set_id, cfg.user_dataset_name, keep_all_lines = keep_all_lines, keep_hetatm_lines = keep_hetatm_lines, tagged_subset = cfg.tagged_subset, extra_rosetta_command_flags = '-ignore_zero_occupancy false -ignore_unrecognized_res', show_full_errors = True, suppress_warnings = suppress_warnings)
        t2 = time.time()

    existing_job = False
    end_job_name  = '%s_%s' % (getpass.getuser(), prediction_set_id)
    if not os.path.exists(job_output_directory):
        os.makedirs(job_output_directory)

    for d in os.listdir(job_output_directory):
        if os.path.isdir(os.path.join(job_output_directory, d)) and end_job_name in d:
            print 'Found existing job:', d
            job_name = d
            existing_job = True
    if not existing_job:
        job_name = '%s-%s' % (time.strftime("%y%m%d"), end_job_name)

    output_dir = os.path.join(job_output_directory, job_name )

    settings['scriptname'] = prediction_set_id + '_run'
    settings['tasks_per_process'] = None
    settings['mem_free'] = None
    settings['output_dir'] = output_dir
    settings['rosetta_args_list'] = []
    settings['rosetta_args_list'].extend(cfg.extra_flags)

    job_dict = {}
    output_data_dir = os.path.join(settings['output_dir'], 'data')

    if not os.path.isdir(output_data_dir):
        os.makedirs(output_data_dir)

    prediction_ids = sorted(ppi_api.get_prediction_ids(prediction_set_id))
    if t1 != None and t2 != None and len(prediction_ids) != 0:
        print('Time taken for {0} predictions: {1}s ({2}s per prediction).'.format(len(prediction_ids), t2-t1, (t2-t1)/len(prediction_ids)))
    print('File cache statistics:')
    pprint.pprint(ppi_api.get_file_content_cache_stats())
    settings['numjobs'] = len(prediction_ids)
    settings['appname'] = None

    print('')

    t1 = time.time()

    # Progress counter setup
    colortext.message('Creating input data for %d predictions.' % (len(prediction_ids)))
    count, records_per_dot = 0, 50
    print("|" + ("*" * (int(len(prediction_ids)/records_per_dot)-2)) + "|")
    for prediction_id in prediction_ids:
        # Progress counter
        count += 1
        if count % records_per_dot == 0: colortext.write(".", "cyan", flush = True)

        # Check if job already ran
        prediction_id_dir = os.path.join(output_dir, str(prediction_id))
        if existing_job:
            if os.path.isdir( prediction_id_dir ):
                pdb_output_files = [x for x in os.listdir( prediction_id_dir ) if '.pdb' in x]
            else:
                pdb_output_files = []
            if len(pdb_output_files) >= 1:
                print 'Skipping', prediction_id
                settings['numjobs'] = settings['numjobs'] - 1
                continue
            if os.path.isdir(prediction_id_dir):
                print 'Job directory %s already exists, deleting' % prediction_id_dir
                shutil.rmtree(prediction_id_dir)

        job_data_dir = os.path.join(output_data_dir, str(prediction_id))

        # Allow us to resume from an interrupted setup
        truncate_content = None
        all_files_exist = os.path.exists(job_data_dir) and os.path.exists(os.path.join(job_data_dir, '.ready'))
        if all_files_exist:
            truncate_content = 0

        job_details = ppi_api.get_job_details(prediction_id, truncate_content = truncate_content)
        file_tuples = [] # List of names, contents
        for file_info in job_details['Files']['Input']:
            file_tuples.append( (file_info['Filename'], file_info['Content']) )
        substitution_parameters = json.loads(job_details['JSONParameters'])

        # Scrub the folder
        if not all_files_exist:
            if os.path.isdir(job_data_dir):
                shutil.rmtree(job_data_dir)
            os.makedirs(job_data_dir)

        files_dict = {} # Maps name to filepath position
        for file_name, file_contents in file_tuples:
            new_file_location = os.path.join(job_data_dir, file_name)
            if not all_files_exist:
                if '.pdb' in file_name:
                    if keep_hetatm_lines or keep_all_lines:
                        write_file(new_file_location, file_contents)
                    else:
                        write_file(new_file_location, '\n'.join([l for l in file_contents.split('\n') if l.startswith('ATOM')]))
                else:
                    with open(new_file_location, 'w') as f:
                        f.write(file_contents)
            files_dict[file_name] = os.path.relpath(new_file_location, settings['output_dir'])
        if not all_files_exist:
            write_file(os.path.join(job_data_dir, '.ready'), '')

        argdict = {
            'input_file_list' : [files_dict[substitution_parameters['%%input_pdb%%']]],
            '%%chainstomove%%' : substitution_parameters['%%chainstomove%%'],
        }
        for file_name, file_location in files_dict.iteritems():
            if 'params' in file_name:
                argdict['-extra_res_fa'] = file_location
        job_dict[prediction_id] = argdict


    t2 = time.time()

    print('')
    if count != 0:
        print('Time taken for {0} predictions: {1}s ({2}s per prediction).'.format(count, t2-t1, (t2-t1)/count))
    print('File cache statistics:')
    pprint.pprint(ppi_api.get_file_content_cache_stats())

    print('')
    if len(job_dict) > 0:
        settings_pickle = os.path.join(output_data_dir, 'settings.pickle')
        job_dict_pickle = os.path.join(output_data_dir, 'blank_job_dict.pickle')
        with open(settings_pickle, 'w') as f:
            pickle.dump(settings, f, protocol = 2)
        with open(job_dict_pickle, 'w') as f:
            pickle.dump(job_dict, f, protocol = 2)
        print 'Settings and job dict dumped to:'
        print settings_pickle
        print job_dict_pickle
        settings_json = os.path.join(output_data_dir, 'settings.json')
        job_dict_json = os.path.join(output_data_dir, 'blank_job_dict.json')
        with open(settings_json, 'w') as f:
            json.dump(settings, f)
        with open(job_dict_json, 'w') as f:
            json.dump(job_dict, f)
        print settings_json
        print job_dict_json
        print
    else:
        print 'No tasks to process, not writing job files'
