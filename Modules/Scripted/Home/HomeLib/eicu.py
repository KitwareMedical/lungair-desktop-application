import numpy as np
import pandas as pd
import os

DTYPE_STRING_MAPPING = {  # Map schema dtype string to pandas dtype string
    'int4': 'int32',  # note that int4 means 4 *bytes* not *bits*
    'int2': 'int16',
    'varchar': 'str',
    'numeric': 'float32'
}

def get_dtype_dict(pasted_table_path):
    """Table schemas can be copied into text files from https://mit-lcp.github.io/eicu-schema-spy/index.html"""
    dtype_dict = {}
    with open(pasted_table_path) as f:
        for line in f.readlines():
            column_name, dtype_string = line.split()[:2]
            if dtype_string not in DTYPE_STRING_MAPPING.keys():
                raise KeyError(f"Please add an entry for {dtype_string} to DTYPE_STRING_MAPPING")
            dtype_dict[column_name] = DTYPE_STRING_MAPPING[dtype_string]
    return dtype_dict

class Eicu:

    def __init__(self, eICU_dir: str, schema_dir: str):
        """Create object to interface with EICU dataset. This reads the tables into memory.

        Args:
            eICU_dir: path to the directory containing the eICU csv.gz tables.
            schema_dir: path to the directory containing the table schema text files.
              (These text files are the pasted table descriptions from https://mit-lcp.github.io/eicu-schema-spy/index.html)
        """

        # Load patient table
        self.patient_df = pd.read_csv(
            os.path.join(eICU_dir, "patient.csv.gz"),
            dtype=get_dtype_dict(os.path.join(schema_dir, "patient.txt")),
            index_col='patientunitstayid',
        )

        # Load respiratory care table
        dtype_dict = get_dtype_dict(os.path.join(schema_dir, "respiratoryCareSchema.txt"))
        dtype_dict['apneaparms'] = 'str'  # Special case because this column is misspelled in csv vs schema
        self.respiratory_care_df = pd.read_csv(
            os.path.join(eICU_dir, "respiratoryCare.csv.gz"),
            dtype=dtype_dict,
        )

        # Load respiratory charting table
        self.respiratory_charting_df = pd.read_csv(
            os.path.join(eICU_dir, "respiratoryCharting_SUBSET.csv"),
            dtype=get_dtype_dict(os.path.join(schema_dir, "respiratoryCharting.txt"))
        )

        self.fio2_df = None

    def get_fio2_df(self):
        """Get a dataframe consisting of the FiO2 entries from the respiratory charting table"""
        if self.fio2_df is None:
            fio2_df = self.respiratory_charting_df[
                (self.respiratory_charting_df['respchartvaluelabel'] == 'FiO2')
                | (self.respiratory_charting_df['respchartvaluelabel'] == 'FIO2 (%)')
            ]

            # add a column that has a float version of the FiO2 value
            self.fio2_df = fio2_df.assign(respchartvalue_float=fio2_df['respchartvalue'].apply(lambda x: x.strip('%')).astype('float32'))
        return self.fio2_df

    def get_random_unitstay(self) -> np.int32:
        """Get a random patient unit stay ID with some constraints (e.g. there is at least one FiO2 entry for the stay).
        This function is meant to help with LungAIR application development in the absence of real NICU patient data,
        by providing a random unit stay ID that we can pretend is the "loaded patient stay" in the application.
        """
        fio2_df = self.get_fio2_df()
        fio2_index = np.random.randint(0, len(fio2_df))
        return fio2_df.iloc[fio2_index]['patientunitstayid']

    def get_patient_from_unitstay(self, unitstay_id: str) -> pd.core.series.Series:
        """Return series of patient data for the patient associated to the given unit stay ID."""
        return self.patient_df.loc[unitstay_id]

    def get_patient_id_from_unitstay(self, unitstay_id: str) -> str:
        return self.get_patient_from_unitstay(unitstay_id)['uniquepid']

    def get_number_of_unit_stays(self, patient_id: str):
        return len(self.patient_df[self.patient_df['uniquepid'] == patient_id])

    def get_number_of_hospital_admissions(self, patient_id: str):
        len(self.patient_df[self.patient_df['uniquepid'] == patient_id]['patienthealthsystemstayid'].unique())

    def process_fio2_data_for_unitstay(self, unitstay_id: str):
        """Given a unit stay ID, this will lookup all the FiO2 data for that unit stay and return some useful information about it.

        We are still experimenting with different ways to aggregate these clinical parameters for viewing and for predictive models.
        This is sort of an experimental function where we can put different features that we'd like to extract.

        Returns:
          fio2_data: a dataframe with two columns:
            respchartoffset: time in minutes since unit admission
            respchartvalue_float: the FiO2 reading recorded for that time
          average_fio2: the average FiO2 value during the unit stay
          bins: a list of pairs representing the start and end of FiO2 % bins, to go with total_times
          total_times: array with the total time, in minutes, spent in each bin from bins
        """
        fio2_df = self.get_fio2_df()
        fio2_for_unitstay = fio2_df[fio2_df['patientunitstayid'] == unitstay_id]
        fio2_data = fio2_for_unitstay[['respchartoffset', 'respchartvalue_float']].sort_values(by='respchartoffset')

        fio2_data_with_deltas = fio2_data.assign(delta_t=fio2_data['respchartoffset'].diff())
        fio2_data_with_deltas = fio2_data_with_deltas.assign(val_shifted=fio2_data_with_deltas['respchartvalue_float'].shift(1))
        total_fio2_time = fio2_data_with_deltas['delta_t'].sum()
        if (total_fio2_time <= 0.):  # It should be possible to have total_fio2_time be 0, if there is just one fio2 entry (so there are no delta_t's)
            if len(fio2_for_unitstay) > 1:  # If that is not what happened, we need to fix this code because that's a case I haven't thought about
                raise Exception(f"Got total time FiO2 time of 0 when trying to integrate, but there is more than one FiO2 entry. Unit stay ID: {unitstay_id}.")
            if len(fio2_for_unitstay) < 1:
                raise ValueError(f"Unit stay id {unitstay_id} has no associated FiO2 data.")
            average_fio2 = fio2_for_unitstay.iloc[0]['respchartvalue_float']
        else:
            # This is basically an integral to compute the average value:
            average_fio2 = (fio2_data_with_deltas['val_shifted'] * fio2_data_with_deltas['delta_t']).sum() / total_fio2_time

        # Compute total time spent within each FiO2 value bin
        bins = [[start, start + 10] for start in range(0, 100, 10)]
        total_times = [fio2_data_with_deltas['delta_t'][(fio2_data_with_deltas['val_shifted'] >= start) & (fio2_data_with_deltas['val_shifted'] < end)].sum()
                       for start, end in bins]

        return fio2_data, average_fio2, bins, total_times
