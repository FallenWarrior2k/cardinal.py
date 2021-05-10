from cardinal.container import RootContainer, _create_engine_wrapper


def test_create_engine_wrapper(mocker):
    create_engine = mocker.patch("cardinal.container.create_engine")
    connect_string = "foo"
    opts = {"a": 1, "b": 2}
    ret = _create_engine_wrapper(connect_string, opts)

    assert ret is create_engine.return_value
    create_engine.assert_called_once_with(connect_string, **opts)
