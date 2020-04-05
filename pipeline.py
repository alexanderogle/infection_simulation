import luigi
import os
import time
import pickle as pkl
from process_inputs import unload_inputs, set_defaults, validate_inputs
from model_engine import InfectionRun
from helpers import sync_s3


class ReadInputs(luigi.Task):
    input_file = luigi.Parameter(default='None')
    send_to_cloud = luigi.BoolParameter(default=False)
    run_id = '{}-{}'.format(
        int(time.time()),
        int(os.getpid())
    )
    path_target = os.path.join('.pipeline_data', str(run_id))
    target = os.path.join(path_target, 'read_inputs.pkl')

    def run(self):
        # Make pipeline_data dir if doesn't exist
        os.makedirs(os.path.join('.pipeline_data',
                                 str(self.run_id)),
                    exist_ok=True)
        inputs = unload_inputs(input_file=self.input_file)

        with open(self.target, 'wb') as file_:
            pkl.dump(inputs, file_)

        if self.send_to_cloud:
            sync_s3('s3://infectionsim-pipeline-data', '.pipeline_data')

    def output(self):
        return luigi.LocalTarget(self.target)


class SetDefaults(luigi.Task):
    input_file = luigi.Parameter(default='None')
    send_to_cloud = luigi.BoolParameter(default=False)
    path_target = ReadInputs.path_target
    target = os.path.join(path_target, 'set_defaults.pkl')

    def requires(self):
        return ReadInputs(input_file=self.input_file, send_to_cloud=self.send_to_cloud)

    def run(self):
        with open(ReadInputs.target, 'rb') as _file:
            inputs = pkl.load(_file)

        inputs = set_defaults(inputs)

        with open(self.target, 'wb') as file_:
            pkl.dump(inputs, file_)

    def output(self):
        return luigi.LocalTarget(self.target)


class ValidateInputs(luigi.Task):
    input_file = luigi.Parameter(default='None')
    send_to_cloud = luigi.BoolParameter(default=False)
    path_target = SetDefaults.path_target
    target = os.path.join(path_target, 'validate_inputs.pkl')

    def requires(self):
        return SetDefaults(input_file=self.input_file, send_to_cloud=self.send_to_cloud)

    def output(self):
        return luigi.LocalTarget(self.target)

    def run(self):
        with open(SetDefaults.target, 'rb') as _file:
            inputs = pkl.load(_file)

        inputs = validate_inputs(inputs)

        with open(self.target, 'wb') as file_:
            pkl.dump(inputs, file_)


class ModelEngine(luigi.Task):
    input_file = luigi.Parameter(default='None')
    send_to_cloud = luigi.BoolParameter(default=False)
    path_target = ValidateInputs.path_target
    target = os.path.join(path_target, 'run_model.pkl')

    def requires(self):
        return ValidateInputs(input_file=self.input_file, send_to_cloud=self.send_to_cloud)

    def output(self):
        return luigi.LocalTarget(self.target)

    def run(self):
        run = InfectionRun(path_inputs=ValidateInputs.target)
        run.setup_population()
        run.setup_network()
        run.run_model()

        with open(self.target, 'wb') as file_:
            pkl.dump(run, file_)


class RunModel(luigi.Task):
    input_file = luigi.Parameter(default='None')
    send_to_cloud = luigi.BoolParameter(default=False)
    path_target = ModelEngine.path_target
    target = os.path.join(path_target, 'sync_to_s3.pkl')

    def requires(self):
        return ModelEngine(input_file=self.input_file, send_to_cloud=self.send_to_cloud)

    def output(self):
        return luigi.LocalTarget(self.target)

    def run(self):
        if self.send_to_cloud:
            sync_s3('.pipeline_data', 's3://infectionsim-pipeline-data')

        with open(self.target, 'wb') as file_:
            pkl.dump('synced', file_)
