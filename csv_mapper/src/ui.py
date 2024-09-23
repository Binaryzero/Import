import json
import os
import sys
import pandas as pd
import re
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QLineEdit,
    QLabel,
    QComboBox,
    QTextEdit,
    QDialog,
    QDialogButtonBox,
)
from PyQt5.QtCore import Qt
from .csv_parser import CSVParser


class FreeformTextDialog(QDialog):
    def __init__(self, parent=None, columns=None):
        super().__init__(parent)
        self.setWindowTitle("Freeform Text Editor")
        self.columns = columns or []
        
        layout = QVBoxLayout(self)
        
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)
        
        column_layout = QHBoxLayout()
        for column in self.columns:
            btn = QPushButton(column)
            btn.clicked.connect(lambda _, col=column: self.insert_column(col))
            column_layout.addWidget(btn)
        
        layout.addLayout(column_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def insert_column(self, column):
        self.text_edit.insertPlainText(f"{{{column}}}")

    def get_text(self):
        return self.text_edit.toPlainText()


class Transformation:
    def __init__(self, name):
        self.name = name
        self.operations = []
        self.new_columns = []

    def add_operation(self, operation):
        self.operations.append(operation)
        # Extract new column names from the operation
        if "df['" in operation:
            new_col = operation.split("df['")[1].split("']")[0]
            if new_col not in self.new_columns:
                self.new_columns.append(new_col)

    def apply(self, df):
        result = df.copy()
        for operation in self.operations:
            exec(operation)
        return result


class MappingUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV Mapper")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # File selection
        file_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setReadOnly(True)
        file_layout.addWidget(self.file_path_input)
        self.select_file_button = QPushButton("Select File")
        self.select_file_button.clicked.connect(self.select_file)
        file_layout.addWidget(self.select_file_button)
        main_layout.addLayout(file_layout)

        # Mapping layout
        mapping_layout = QHBoxLayout()

        # Source columns
        source_layout = QVBoxLayout()
        source_layout.addWidget(QLabel("Source Columns"))
        self.source_list = QListWidget()
        source_layout.addWidget(self.source_list)

        # Transformation options
        transform_layout = QVBoxLayout()
        transform_layout.addWidget(QLabel("Transformations"))
        self.add_transform_button = QPushButton("Add Transformation")
        self.add_transform_button.clicked.connect(self.add_transformation)
        self.edit_transform_button = QPushButton("Edit Transformation")
        self.edit_transform_button.clicked.connect(self.edit_transformation)
        transform_layout.addWidget(self.add_transform_button)
        transform_layout.addWidget(self.edit_transform_button)

        # Target columns
        target_layout = QVBoxLayout()
        target_layout.addWidget(QLabel("Target Columns"))
        self.target_list = QListWidget()
        self.target_list.setDragDropMode(
            QListWidget.InternalMove
        )  # Enable drag and drop
        self.target_list.setSelectionMode(
            QListWidget.ExtendedSelection
        )  # Allow multiple selection
        target_layout.addWidget(self.target_list)
        button_layout = QVBoxLayout()
        # Buttons
        self.map_button = QPushButton("Map Column", self)
        self.map_button.clicked.connect(self.map_column)
        self.unmap_button = QPushButton("<< Unmap")
        self.unmap_button.clicked.connect(self.unmap_column)
        button_layout.addWidget(self.map_button)
        button_layout.addWidget(self.unmap_button)
        # Export button
        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_csv)
        button_layout.addWidget(self.export_button)
        # Save/Load mapping buttons
        self.save_mapping_button = QPushButton("Save Mapping")
        self.save_mapping_button.clicked.connect(self.save_mapping)
        button_layout.addWidget(self.save_mapping_button)

        self.load_mapping_button = QPushButton("Load Mapping")
        self.load_mapping_button.clicked.connect(self.load_mapping)
        button_layout.addWidget(self.load_mapping_button)

        self.export_script_button = QPushButton("Export as Script")
        self.export_script_button.clicked.connect(self.export_as_script)
        button_layout.addWidget(self.export_script_button)

        mapping_layout.addLayout(source_layout)
        mapping_layout.addLayout(transform_layout)
        mapping_layout.addLayout(target_layout)
        mapping_layout.addLayout(button_layout)
        main_layout.addLayout(mapping_layout)

        self.csv_parser = None
        self.source_column_combo = QComboBox()  # Initialize source_column_combo
        self.mappings = {}
        self.transformations = {}

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv)"
        )
        if file_path:
            self.load_csv(file_path)

    def load_csv(self, file_path):
        try:
            self.csv_data = pd.read_csv(file_path)
            self.update_ui_with_csv_data()
            self.file_path_input.setText(file_path)
            QMessageBox.information(self, "Success", "CSV file loaded successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV: {str(e)}")
            self.csv_data = None

    def update_ui_with_csv_data(self):
        self.source_column_combo.clear()
        self.source_list.clear()
        if (
            hasattr(self, "csv_data")
            and self.csv_data is not None
            and not self.csv_data.empty
        ):
            for column in self.csv_data.columns:
                self.source_column_combo.addItem(column)
                self.source_list.addItem(column)

        # Ensure the combo box and source list are visible and enabled
        self.source_column_combo.setVisible(False)
        self.source_column_combo.setEnabled(False)
        self.source_list.setVisible(True)
        self.source_list.setEnabled(True)

        # Force the main window to update
        self.update()
        QApplication.processEvents()

    def populate_source_columns(self, columns):
        self.source_list.clear()
        self.source_list.addItems(columns)

    def map_column(self):
        selected_items = self.source_list.selectedItems()
        for item in selected_items:
            column_name = item.text()
            if column_name.startswith("Transformation: "):
                transform_name = column_name.split(": ")[1]
                self.mappings[transform_name] = self.transformations[transform_name]
            else:
                if column_name not in self.mappings:
                    self.mappings[column_name] = {"type": "passthrough"}

            # Remove the item from the source list
            self.source_list.takeItem(self.source_list.row(item))

        self.update_target_list()

    def unmap_column(self):
        selected_items = self.target_list.selectedItems()
        for item in selected_items:
            column_name = item.text()

            # Handle renamed columns
            if " -> " in column_name:
                column_name = column_name.split(" -> ")[0]

            # Handle split columns
            if " (split by " in column_name:
                column_name = column_name.split(" (split by ")[0]

            # Handle filtered columns
            if " (filtered: " in column_name:
                column_name = column_name.split(" (filtered: ")[0]

            new_item = QListWidgetItem(column_name)
            self.source_list.addItem(new_item)
            self.target_list.takeItem(self.target_list.row(item))

            if column_name.startswith("Transformation: "):
                transform_name = column_name.split(": ")[1]
                if transform_name in self.mappings:
                    del self.mappings[transform_name]
            elif column_name in self.mappings:
                del self.mappings[column_name]

        self.update_target_list()

    def dropEvent(self, event):
        if event.source() == self.target_list:
            event.accept()
        else:
            event.ignore()

    def export_csv(self):
        if self.csv_data is None:
            QMessageBox.warning(self, "Warning", "Please load a CSV file first.")
            return

        if not self.mappings:
            QMessageBox.warning(
                self,
                "Warning",
                "No mappings defined. Please add at least one transformation before exporting.",
            )
            return

        export_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "", "CSV Files (*.csv)"
        )
        if not export_path:
            return  # User cancelled the file dialog

        try:
            # Apply the transformations
            transformed_data = self.apply_transformations()

            if transformed_data.empty:
                QMessageBox.warning(
                    self, "Warning", "No data to export after applying transformations."
                )
                return

            # Get all columns from the target list
            targeted_columns = []
            for item in self.target_list.findItems("*", Qt.MatchWildcard):
                text = item.text()
                if text.startswith("Transformation: "):
                    transform_name = text.split(": ")[1]
                    if transform_name in self.transformations:
                        targeted_columns.extend(
                            [
                                col
                                for col in transformed_data.columns
                                if col.startswith(transform_name)
                            ]
                        )
                else:
                    targeted_columns.append(text)

            # Remove duplicates while preserving order
            targeted_columns = list(dict.fromkeys(targeted_columns))

            # Ensure all targeted columns exist in the transformed data
            existing_columns = [
                col for col in targeted_columns if col in transformed_data.columns
            ]

            if len(existing_columns) < len(targeted_columns):
                missing_columns = set(targeted_columns) - set(existing_columns)
                missing_columns = [
                    col
                    for col in missing_columns
                    if not col.startswith("Transformation: ")
                ]
                if missing_columns:
                    QMessageBox.warning(
                        self,
                        "Warning",
                        f"Some targeted columns are missing from the transformed data: {', '.join(missing_columns)}",
                    )

            # Export only the transformed and mapped data
            transformed_data[existing_columns].to_csv(export_path, index=False)
            QMessageBox.information(
                self, "Success", f"CSV exported successfully to {export_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {str(e)}")

    def apply_transformations(self):
        if self.csv_data is None:
            raise Exception("No CSV data loaded. Please select a file first.")

        result = self.csv_data.copy()

        for source, transform in self.mappings.items():
            if isinstance(transform, Transformation):
                result = transform.apply(result)

        return result

    def save_mapping(self):
        if self.target_list.count() == 0:
            # Show an error message if no columns are mapped
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Mapping", "", "JSON Files (*.json)"
        )
        if save_path:
            mapping = {
                "source_file": self.file_path_input.text(),
                "mapped_columns": [
                    self.target_list.item(i).text()
                    for i in range(self.target_list.count())
                ],
            }
            with open(save_path, "w") as f:
                json.dump(mapping, f)

    def load_mapping(self):
        load_path, _ = QFileDialog.getOpenFileName(
            self, "Load Mapping", "", "JSON Files (*.json)"
        )
        if load_path:
            with open(load_path, "r") as f:
                mapping = json.load(f)

            if mapping["source_file"] != self.file_path_input.text():
                # Show a warning that the mapping was created for a different file
                pass

            self.target_list.clear()
            self.target_list.addItems(mapping["mapped_columns"])

            # Remove mapped columns from source_list
            for column in mapping["mapped_columns"]:
                items = self.source_list.findItems(column, Qt.MatchExactly)
                if items:
                    self.source_list.takeItem(self.source_list.row(items[0]))

    def add_transformation(self):
        name, ok = QInputDialog.getText(
            self, "New Transformation", "Enter transformation name:"
        )
        if ok and name:
            self.transformations[name] = Transformation(name)
            self.edit_transformation(name)
            self.source_list.addItem(f"Transformation: {name}")
            self.update_target_list()

    def update_target_list(self):
        self.target_list.clear()
        for source, transform in self.mappings.items():
            if isinstance(transform, Transformation):
                self.target_list.addItem(f"Transformation: {transform.name}")
            else:
                # Handle regular columns
                if transform.get("type") == "rename":
                    self.target_list.addItem(f"{source} -> {transform['new_name']}")
                elif transform.get("type") == "combine":
                    self.target_list.addItem(
                        f"{source} + {transform['combine_with']} -> {transform['new_name']}"
                    )
                elif transform.get("type") == "split":
                    self.target_list.addItem(
                        f"{source} (split by {transform['delimiter']})"
                    )
                elif transform.get("type") == "filter":
                    self.target_list.addItem(
                        f"{source} (filtered: {transform['condition']})"
                    )
                else:
                    self.target_list.addItem(source)

    def edit_transformation(self, name=None):
        if name is None:
            name, ok = QInputDialog.getItem(
                self,
                "Edit Transformation",
                "Select transformation to edit:",
                list(self.transformations.keys()),
                0,
                False,
            )
            if not ok:
                return

        transformation = self.transformations[name]

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Transformation: {name}")
        layout = QVBoxLayout(dialog)

        operation_list = QListWidget()
        for op in transformation.operations:
            operation_list.addItem(str(op))
        layout.addWidget(operation_list)

        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Operation")
        edit_button = QPushButton("Edit Operation")
        delete_button = QPushButton("Delete Operation")
        done_button = QPushButton("Done")

        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(done_button)
        layout.addLayout(button_layout)

        add_button.clicked.connect(
            lambda: self.add_operation(transformation, operation_list)
        )
        edit_button.clicked.connect(
            lambda: self.edit_operation(transformation, operation_list)
        )
        delete_button.clicked.connect(
            lambda: self.delete_operation(transformation, operation_list)
        )
        done_button.clicked.connect(dialog.accept)

        dialog.exec_()
        self.update_target_list()

    def add_operation(self, transformation, operation_list):
        operation_types = ["Custom", "Rename", "Combine", "Split", "Filter", "Freeform Text"]
        operation_type, ok = QInputDialog.getItem(
            self, "Add Operation", "Select operation type:", operation_types, 0, False
        )

        if ok:
            if operation_type == "Freeform Text":
                dialog = FreeformTextDialog(self, columns=list(self.csv_data.columns))
                if dialog.exec_():
                    template = dialog.get_text()
                    new_column_name, ok = QInputDialog.getText(
                        self, "New Column", "Enter name for the new column:"
                    )
                    if ok:
                        # Extract placeholders and their corresponding column names
                        placeholders = re.findall(r'\{([^}]+)\}', template)
                        
                        # Create the operation code
                        operation_code = f"template = '''{template}'''\n"
                        operation_code += f"df['{new_column_name}'] = df.apply(lambda row: template.format("
                        
                        # Generate the format arguments
                        format_args = []
                        for placeholder in placeholders:
                            # Use dictionary-style string formatting for column names with spaces
                            format_args.append(f"**{{'{placeholder}': row['{placeholder}']}}")
                        
                        operation_code += ", ".join(format_args)
                        operation_code += "), axis=1)\n"
                        
                        transformation.add_operation(operation_code)
                        operation_list.addItem(f"Freeform Text: {new_column_name}")
            elif operation_type == "Custom":
                custom_code, ok = QInputDialog.getMultiLineText(
                    self, "Custom", "Enter custom transformation code:"
                )
                if ok:
                    transformation.add_operation(custom_code)
                    operation_list.addItem(f"Custom: {custom_code.split('\n')[0]}...")
            elif operation_type == "Rename":
                old_name = self.get_column_selection("Select column to rename")
                new_name, ok = QInputDialog.getText(
                    self, "Rename", "Enter new column name:"
                )
                if ok:
                    operation_code = (
                        f"df = df.rename(columns={{'{old_name}': '{new_name}'}})"
                    )
                    transformation.add_operation(operation_code)
                    operation_list.addItem(f"Rename: {old_name} -> {new_name}")
            elif operation_type == "Combine":
                col1 = self.get_column_selection("Select first column to combine")
                col2 = self.get_column_selection("Select second column to combine")
                new_name, ok = QInputDialog.getText(
                    self, "Combine", "Enter new column name:"
                )
                if ok:
                    operation_code = (
                        f"df['{new_name}'] = df['{col1}'] + ' ' + df['{col2}']"
                    )
                    transformation.add_operation(operation_code)
                    operation_list.addItem(f"Combine: {col1} + {col2} -> {new_name}")
            elif operation_type == "Split":
                col = self.get_column_selection("Select column to split")
                delimiter, ok = QInputDialog.getText(self, "Split", "Enter delimiter:")
                if ok:
                    operation_code = (
                        f"df['{col}_split'] = df['{col}'].str.split('{delimiter}')"
                    )
                    transformation.add_operation(operation_code)
                    operation_list.addItem(f"Split: {col} (delimiter: {delimiter})")
            elif operation_type == "Filter":
                col = self.get_column_selection("Select column to filter")
                condition, ok = QInputDialog.getText(
                    self, "Filter", f"Enter filter condition for {col} (e.g., > 5):"
                )
                if ok:
                    operation_code = (
                        f"df = df[df['{col}'].astype(str).eval('{condition}')]"
                    )
                    transformation.add_operation(operation_code)
                    operation_list.addItem(f"Filter: {col} {condition}")

    def get_column_selection(self, prompt):
        columns = list(self.csv_data.columns)
        column, ok = QInputDialog.getItem(
            self, prompt, "Select column:", columns, 0, False
        )
        if ok:
            return column
        return None

    def edit_operation(self, transformation, operation_list):
        if not operation_list.currentItem():
            QMessageBox.warning(self, "Warning", "Please select an operation to edit.")
            return

        current_index = operation_list.currentRow()
        current_operation = transformation.operations[current_index]

        # Here you would implement the logic to edit the selected operation
        # This could involve creating a new dialog with fields specific to each operation type
        # For simplicity, we'll just remove the old operation and add a new one
        self.delete_operation(transformation, operation_list)
        self.add_operation(transformation, operation_list)

    def delete_operation(self, transformation, operation_list):
        if not operation_list.currentItem():
            QMessageBox.warning(
                self, "Warning", "Please select an operation to delete."
            )
            return

        current_index = operation_list.currentRow()
        transformation.operations.pop(current_index)
        operation_list.takeItem(current_index)

    def export_as_script(self):
        if not self.mappings:
            QMessageBox.warning(
                self,
                "Warning",
                "No mappings defined. Please add at least one transformation before exporting.",
            )
            return

        script_path, _ = QFileDialog.getSaveFileName(
            self, "Export Python Script", "", "Python Files (*.py)"
        )
        if not script_path:
            return

        try:
            with open(script_path, 'w') as script_file:
                script_file.write("import pandas as pd\n")
                script_file.write("from config import INPUT_CSV_PATH, OUTPUT_CSV_PATH\n\n")
                script_file.write("def apply_transformations(df):\n")
                
                for source, transform in self.mappings.items():
                    if isinstance(transform, Transformation):
                        script_file.write(f"    # Applying transformation: {transform.name}\n")
                        for operation in transform.operations:
                            # Ensure proper indentation for each line of the operation
                            indented_operation = "\n".join("    " + line for line in operation.split("\n"))
                            script_file.write(f"{indented_operation}\n")
                        script_file.write("\n")

                # Get the targeted columns
                targeted_columns = []
                for item in self.target_list.findItems("*", Qt.MatchWildcard):
                    text = item.text()
                    if text.startswith("Transformation: "):
                        transform_name = text.split(": ")[1]
                        if transform_name in self.transformations:
                            for op in self.transformations[transform_name].operations:
                                if isinstance(op, str) and "df['" in op:
                                    new_col = op.split("df['")[1].split("']")[0]
                                    targeted_columns.append(f"'{new_col}'")
                    else:
                        targeted_columns.append(f"'{text}'")

                script_file.write("    # Select only the targeted columns\n")
                script_file.write(f"    targeted_columns = [{', '.join(targeted_columns)}]\n")
                script_file.write("    df = df[targeted_columns]\n")
                script_file.write("    return df\n\n")
                script_file.write("if __name__ == '__main__':\n")
                script_file.write("    df = pd.read_csv(INPUT_CSV_PATH)\n")
                script_file.write("    transformed_df = apply_transformations(df)\n")
                script_file.write("    transformed_df.to_csv(OUTPUT_CSV_PATH, index=False)\n")
                script_file.write("    print(f'Transformed CSV saved to {OUTPUT_CSV_PATH}')\n")

            QMessageBox.information(
                self, "Success", f"Python script exported successfully to {script_path}"
            )
            QMessageBox.information(self, "Next Steps", "Please ensure you have a 'config.py' file in the same directory as the exported script with INPUT_CSV_PATH and OUTPUT_CSV_PATH defined.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to export Python script: {str(e)}"
            )


if __name__ == "__main__":
    app = QApplication([])
    window = MappingUI()
    window.show()
    app.exec_()
