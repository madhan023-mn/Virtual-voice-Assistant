import commands

def test_route(q):
    res = commands.route_command(q)
    print(f"[{q}] -> {res}")

test_route("define apple")
test_route("inspire me")
test_route("where am i")
test_route("where is paris")
test_route("movie inception")
test_route("holidays in us")
test_route("nasa picture of the day")
test_route("play coldplay on spotify")
test_route("generate image of a cat")
