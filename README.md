# senscritique_books_csvmaker
Designed to extract books (and comics) from senscritique as csv-compatible-with-goodreads (or storygraph)
It works (september 2025)

# target
Extract comics and books collections to a csv that can be imported in goodreads or storygraph 's apps.
It gathers only books with ratings

# installation
install requirements
$ pip install -r requirements.txt

# setup
edit the only main script to:
- add your account (USERNAME) and your SC_AUTH_COOKIE (can be found with your browser > local storage > cookie)
- you can retrieved books and/or comics (WHICH_COLLECTIONS)
- change the csv output path

# execution
execute the script with:
$ python scrap_senscritique.py
and wait...

# what to do next
go to your storygraph's account, click on the top right of your very own avatar
Manage Account, then "Goodreads import" > Imports Goodreads Library, drop the csv on step 2 and click on the big green button

# epilogue
you shall continue to use your senscritique account as well as your storygraph's, that's two beautiful tool to discover beautiful new things