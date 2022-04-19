from datadome.browser import DatadomeSolver

def test_rakuten():
    b = DatadomeSolver()
    response = b.go_to('https://fr.shopping.rakuten.com/event/jeux-video-et-consoles')
    print(response)

def test_leboncoin():
    b = DatadomeSolver(proxy_pool='smartproxy')
    response = b.go_to('https://www.leboncoin.fr/recherche?category=9&locations=d_87&real_estate_type=1%2C2')
    print(response)

if __name__=="__main__":
    test_leboncoin()