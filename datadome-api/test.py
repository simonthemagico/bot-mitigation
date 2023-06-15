from datadome.browser import DatadomeSolver

def test_rakuten():
    b = DatadomeSolver(
        proxy_pool='smartproxy-dc',
        domain='fr.shopping.rakuten.com',
    )
    b.set_random_proxy()
    response = b.go_to('https://fr.shopping.rakuten.com/event/jeux-video-et-consoles')
    print(response)

def test_leboncoin():
    b = DatadomeSolver(
        proxy_pool='smartproxy-full',
        domain='.leboncoin.fr',
        origin='https://www.leboncoin.fr',
        dd_endpoint='dd.leboncoin.fr'
    )
    response = b.go_to('https://www.leboncoin.fr/recherche?category=9&locations=d_87&real_estate_type=1%2C2')
    print(response)

def test_pointp():
    b = DatadomeSolver(proxy_pool='smartproxy-dc')
    response = b.go_to('https://www.pointp.fr/p/bois-et-panneaux/dalle-bois-dalle-kronoply-osb3-krono-milieu-humide-4-rainures-A1842460')
    print(response)

if __name__=="__main__":
    # test_rakuten()
    # test_leboncoin()
    test_pointp()