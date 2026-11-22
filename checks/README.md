# checks/

Scripts used while working on the paper, kept so that the reasoning behind the
figures can be followed. They are not needed to reproduce any published number;
`reproduce.py` in the top folder does that.

    render_field.py     draw the near field of a row from a field dump
    fig_tiers.py        pixel maps of the three coupling lengths side by side
    verify_tier.py      per-row contrast and error count for one coupling length
    row_margin.py       how much room each row has between its dimmest bright
                        pixel and its brightest dark pixel
    tile_crosstalk.py   how much one addressed row leaks into the rows around it

They read the field dumps and the per-row records that the wave simulations
write, so they only run on the machine that produced those files. Nothing here
is imported by the four top-level scripts.

One habit these scripts enforce: any figure that puts several runs side by side
uses **one colour scale** for all of them. Normalising each panel separately
once hid an 81 % change in the data.
