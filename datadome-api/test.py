from datadome.browser import DatadomeSolver

if __name__=="__main__":
    b = DatadomeSolver()
    response = b.go_to('https://fr.shopping.rakuten.com/event/jeux-video-et-consoles')
    print(response)