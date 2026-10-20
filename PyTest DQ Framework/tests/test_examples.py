import pytest


@pytest.fixture(scope='module')
def target_data(db_connection):
    target_query = """
    SELECT ...
    """
    target_data = db_connection.get_data_sql(target_query)
    return target_data


@pytest.fixture(scope='module')
def source_data(parquet_reader):
    target_path = '/root/path/to/file'
    target_data = parquet_reader.process(target_path)
    return target_data


@pytest.mark.example
def test_check_dataset_is_not_empty(target_data, data_quality_library):
    data_quality_library.check_dataset_is_not_empty(target_data)


@pytest.mark.example
def test_check_count(source_data, target_data, data_quality_library):
    data_quality_library.check_count(source_data, target_data)
