# Creating Web Serial config files

If you want to create a config file for the scraper, this little step-by-step guide will help you out.
Also check out the documented example config in scraper/configs/Wandering_Inn_Volume_1.yaml.

Working configs can gladly be added by Pull Request.

If you're stuck with something or your config doesn't work, feel free to request help by opening a Issue.

## User Data directories

Windows: `C:\Users\USERNAME\AppData\Local\Curetix\WebFictionScraper`

Linux: `/home/USERNAME/.local/share/WebFictionScraper`

Mac OS: `/Users/USERNAME/Library/Application Support/WebFictionScraper`

## Basics

Config files for the scraper use the YAML format. Start by creating a file inside the `configs` subdirectory of the user data dir.

The file extension has to be .yaml and it's best to keep the name short,
since you'll have to type it everytime you want to run the scraper with said config.

## URLs and Metadata

Let's start with the most simple option. The **startUrl** key is the URL of the web serial's first chapter, like so:

```yaml
startUrl: https://wanderinginn.com/2016/07/27/1-00/
```

You can also specify an **endUrl** after which the scraper would stop looking for further chapters, as well as a list of chapter URLs to completely skip:

```yaml
endUrl: https://wanderinginn.com/2017/03/04/1-45/
skipChapters:
  - https://some.chapter/to/skip
```

Next is the metadata of the fiction, which is all pretty self-explanatory:

```yaml
metadata:
  title: The Wandering Inn - Volume 1
  author: pirateaba
  description: |
    "No killing Goblins."

    So reads the sign outside of the Wandering Inn, a small building run by a young woman named Erin Solstice. She serves pasta with sausage, blue fruit juice, and dead acid flies on request. And she comes from another world. Ours.
    
    It's a bad day when Erin finds herself transported to a fantastical world and nearly gets eaten by a dragon. She doesn't belong in a place where monster attacks are a fact of life, and where humans are one species among many. But she must adapt to her new life. Or die.
    
    In a dangerous world where magic is real and people can level up and gain classes, Erin Solstice must battle somewhat evil Goblins, deadly Rock Crabs, and hungry [Necromancers]. She is no [Warrior], no [Mage]. Erin Solstice runs an inn.
    
    She's an [Innkeeper].
```

Only **title** and **author** are required. Note how the description: the vertical dash allows you to use paragraphs and new lines.

For more optional metadata keys look into the example config mentioned at the start.

## Files

All of these options are optional (hah).