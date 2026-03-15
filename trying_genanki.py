import genanki 
my_deck=genanki.Deck(2059400110,'My Deck')
my_model = genanki.Model(
  1607392319,
  'Simple Model',
  fields=[
    {'name': 'Question'},
    {'name': 'Answer'},
  ],
  templates=[
    {
      'name': 'Card 1',
      'qfmt': '{{Question}}',
      'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
    },
  ])


my_note = genanki.Note(model=my_model, fields=['What is the capital of France?','Paris'])
my_deck.add_note(my_note)
genanki.Package(my_deck).write_to_file('output.apkg')
print("Anki deck created successfully!")