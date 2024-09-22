import pandas as pd
import csv


class CSVParser:
    def __init__(self, file_path=None):
        self.header = []  # Initialize the header as an empty list
        self.data = []    # Initialize the data as an empty list
        if file_path:
            self.load_csv(file_path)

    def load_csv(self, file_path):
        with open(file_path, 'r') as file:
            csv_reader = csv.reader(file)
            self.header = next(csv_reader)  # Set the header
            self.data = list(csv_reader)    # Set the data

    def get_columns(self):
        if self.data is not None:
            return list(self.data.columns)
        return []

    def get_preview(self, rows=5):
        if self.data is not None:
            return self.data.head(rows)
        return None

    def export_csv(self, export_path, mapped_columns):
        try:
            with open(export_path, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(mapped_columns)  # Write the new header

                for row in self.data:
                    new_row = []
                    for old_col in mapped_columns:
                        if old_col in self.header:
                            index = self.header.index(old_col)
                            new_row.append(row[index])
                        else:
                            new_row.append('')  # or some default value
                    writer.writerow(new_row)

        except Exception as e:
            print(f"Error processing row {row}: {str(e)}")
            print(f"Row data: {row}")
            print(f"Header: {self.header}")
            raise  # Re-raise the exception for further handling
