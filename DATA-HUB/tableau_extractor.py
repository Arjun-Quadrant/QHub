import xml.etree.ElementTree as ET
import pandas as pd


# 🔹 Extract and Save Metadata
def extract_datasource_metadata():
    workbook_path = r"C:\Users\arjun\Quadrant\tableau_to_power_bi_project\Repos\QHub\DATA-HUB\Workbooks\Superstore.twb"
    tree = ET.parse(workbook_path)
    root = tree.getroot()
    datasources = []
    for datasource in root.findall("datasources/datasource"):
        datasource_name = datasource.get("caption")
        connections = datasource.findall("connection")
        for connection in connections:
            connection_details = connection.find(".//connection")
            connection_type = connection_details.get("class")
            file_path = None
            tables = None
            if connection_type == "textscan":
                file_path = fr"{connection_details.get("directory")}/{connection_details.get("filename")}"
                tables = connection.findall("relation")
                for table in tables:
                    tableName = table.get("name")
                    tableName = tableName[:tableName.index(".")]
                    columns = table.findall("columns/column")
                    columnNames = []
                    for column in columns:
                        columnNames.append(column.get("name"))
                    columnNames = ", ".join(columnNames)
                    datasources.append({
                        "Data Source": datasource_name,
                        "Connection Info": file_path,
                        "Data Table Name": tableName,
                        "Column Names": columnNames
                    })
            elif connection_type == "excel-direct":
                file_path = fr"{connection_details.get("directory")}/{connection_details.get("filename")}"
                tables = connection.findall("relation")
                if tables[0].get("type") == "collection":
                    # There is more than one sheet in the Excel workbook
                    tables = tables[0].findall("relation")
                for table in tables:
                    tableName = table.get("name")
                    columns = table.findall("columns/column")
                    columnNames = []
                    for column in columns:
                        columnNames.append(column.get("name"))
                    columnNames = ", ".join(columnNames)
                    datasources.append({
                        "Data Source": datasource_name,
                        "Connection Info": file_path,
                        "Data Table Name": tableName,
                        "Column Names": columnNames
                    })
            elif connection_type == "hyper":
                file_path = connection_details.get("dbname")
                tables = connection.findall("relation")
                table_to_columns = {}
                for table in tables:
                    tableName = table.get("name")
                    table_to_columns[tableName] = []
                columnInfo = connection.findall("metadata-records/metadata-record")
                for c in columnInfo:
                    c_name = c.find("local-name").text[1:-1]
                    c_parent = c.find("parent-name").text[1:-1]
                    table_to_columns.get(c_parent).append(c_name)

                for tableName in table_to_columns:
                    columnNames = ", ".join(table_to_columns[tableName])
                    datasources.append({
                        "Data Source": datasource_name,
                        "Connection Info": file_path,
                        "Data Table Name": tableName,
                        "Column Names": columnNames
                    })
    return datasources

def extract_parameter_metadata():
    workbook_path = r"C:\Users\arjun\Quadrant\tableau_to_power_bi_project\Repos\QHub\DATA-HUB\Workbooks\World Indicators.twb"
    tree = ET.parse(workbook_path)
    root = tree.getroot()
    parameters = []
    parameter_datasource = root.find("datasources/datasource[@name='Parameters']")
    if parameter_datasource is not None:
        column_info = parameter_datasource.find("column")
        caption = column_info.get("caption")
        data_type = column_info.get("datatype")
        format = column_info.get("default-format")
        name = column_info.get("name")
        domain_type = column_info.get("param-domain-type")
        role = column_info.get("role")
        type = column_info.get("type")
        default_value = column_info.get("value")
        range_info = column_info.find("range")
        range_granularity = range_info.get("granularity")
        range_max = range_info.get("max")
        range_min = range_info.get("min")
        parameters.append({
            "Caption": caption,
            "Data Type": data_type,
            "Format": format,
            "Name": name,
            "Domain Type": domain_type,
            "Role": role,
            "Type": type,
            "Default Value": default_value,
            "Range Granularity": range_granularity,
            "Range Min": range_min,
            "Range Max": range_max
        })
    return parameters

def get_mapping():
    column_to_table_mapping = {}
    workbook_path = r"C:\Users\arjun\Quadrant\tableau_to_power_bi_project\Repos\QHub\DATA-HUB\Workbooks\Superstore.twb"
    tree = ET.parse(workbook_path)
    root = tree.getroot()
    datasources = root.findall("./datasources/datasource")
    print(datasources)
    for datasource in datasources:
        for map in datasource.findall("connection/cols/map"):
            column = map.get("key")
            table = map.get("value").split(".")[0][1:-1]
            column_to_table_mapping[column] = table
    return column_to_table_mapping

def extract_visualization_metadata():
    workbook_path = r"C:\Users\arjun\Quadrant\tableau_to_power_bi_project\Repos\QHub\DATA-HUB\Workbooks\World Indicators.twb"
    tree = ET.parse(workbook_path)
    root = tree.getroot()
    visualizations = []
    for visualization in root.findall(".//worksheets/worksheet"):
        # the default
        visualization_title_text = "No title"
        visualization_title_element = visualization.find(".//title")
        if visualization_title_element is not None:
            visualization_title_text = ""
            for run in visualization_title_element.findall(".//run"):
                visualization_title_text = visualization_title_text + run.text
        
        mark_types = []
        for pane in visualization.findall(".//panes/pane"):
            mark_types.append(pane.find("mark").get("class"))
        mark_types = ", ".join(mark_types)

        datasources = []
        for datasource in visualization.findall(".//datasources/datasource"):
            datasource_name = datasource.get("name")
            datasource_caption = "None"
            if datasource_name != "Parameters":
                datasource_caption = datasource.get("caption")

            # for datasource_info in visualization.findall(f".//datasource-dependencies[@name='{datasource_name}']"):
                

        visualizations.append({
            "Visualization Title": visualization_title_text,
            "Mark Types": mark_types
        })
    return visualizations

def adjust_column_widths(dataframe, worksheet):
    for idx, col in enumerate(dataframe):
        series = dataframe[col]
        max_len = max((
        series.astype(str).map(len).max(),  # len of largest item
        len(str(series.name))  # len of column name/header
        )) + 1  # adding a little extra space
        worksheet.set_column(idx, idx, max_len)

# 🔹 Run the Extraction
if __name__ == "__main__":

    mapping = get_mapping()
    print(mapping)
    exit()

    datasources = extract_datasource_metadata()
    df_datasources = pd.DataFrame(datasources)

    # parameters = extract_parameter_metadata()
    # df_parameters = pd.DataFrame(parameters)

    # visualizations = extract_visualization_metadata()
    # df_visualizations = pd.DataFrame(visualizations)

    with pd.ExcelWriter("superstore_workbook_datasource_metadata.xlsx") as writer:
        df_datasources.to_excel(writer, sheet_name="Datasources", index=False)
        worksheet = writer.sheets["Datasources"]
        adjust_column_widths(df_datasources, worksheet)

    #     df_parameters.to_excel(writer, sheet_name="Parameters", index=False)
    #     worksheet = writer.sheets["Parameters"]
    #     adjust_column_widths(df_parameters, worksheet)

        # df_visualizations.to_excel(writer, sheet_name="Visualizations", index=False)
        # worksheet = writer.sheets["Visualizations"]
        # adjust_column_widths(df_visualizations, worksheet)