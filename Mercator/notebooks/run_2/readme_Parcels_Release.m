## Read me

Each job = 1 node (256 CPU threads, 250 G RAM), notebook v3.Run_parcels_UVW_adaptive.ipynb.
Releases every 5 days (offsets = days after 1993-01-01), 2 years per block, last release 2013-12-28 (as run_1 tracks_78876).
Each chunk has ~37 notebooks, run 19 at a time on its node (~1.5 h per chunk).

sbatch v1.Run_parcels_UVW.sh <first offset> <last offset> <seed>   -> tracks_v3_<seed>/

Seeds:  11098723  1993-1998
          45678   1999-2004
          67891   2005-2008
          78876   2009-2013

All jobs, max 4 running at a time:  bash v1.Submit_chains.sh
Rerun single notebooks:             sbatch v3.Rerun_offset.sh <seed> <offset> ...

# 1993-1994 (146 notebooks) - done
# sbatch v1.Run_parcels_UVW.sh 0    # offsets   5-185  (37 notebooks)
# sbatch v1.Run_parcels_UVW.sh 1    # offsets 190-370  (37 notebooks)
# sbatch v1.Run_parcels_UVW.sh 2    # offsets 375-555  (37 notebooks)
# sbatch v1.Run_parcels_UVW.sh 3    # offsets 560-730  (35 notebooks)

# 1995-1996 (146 notebooks), seed 11098723
sbatch v1.Run_parcels_UVW.sh  731  911 11098723   # 1995-01-02 to 1995-07-01  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh  916 1096 11098723   # 1995-07-06 to 1996-01-02  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 1101 1276 11098723   # 1996-01-07 to 1996-06-30  (36 notebooks)
sbatch v1.Run_parcels_UVW.sh 1281 1456 11098723   # 1996-07-05 to 1996-12-27  (36 notebooks)

# 1997-1998 (146 notebooks), seed 11098723
sbatch v1.Run_parcels_UVW.sh 1461 1641 11098723   # 1997-01-01 to 1997-06-30  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 1646 1826 11098723   # 1997-07-05 to 1998-01-01  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 1831 2006 11098723   # 1998-01-06 to 1998-06-30  (36 notebooks)
sbatch v1.Run_parcels_UVW.sh 2011 2186 11098723   # 1998-07-05 to 1998-12-27  (36 notebooks)

# 1999-2000 (147 notebooks), seed 45678
sbatch v1.Run_parcels_UVW.sh 2191 2371    45678   # 1999-01-01 to 1999-06-30  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 2376 2556    45678   # 1999-07-05 to 2000-01-01  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 2561 2741    45678   # 2000-01-06 to 2000-07-04  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 2746 2921    45678   # 2000-07-09 to 2000-12-31  (36 notebooks)

# 2001-2002 (146 notebooks), seed 45678
sbatch v1.Run_parcels_UVW.sh 2926 3106    45678   # 2001-01-05 to 2001-07-04  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 3111 3291    45678   # 2001-07-09 to 2002-01-05  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 3296 3471    45678   # 2002-01-10 to 2002-07-04  (36 notebooks)
sbatch v1.Run_parcels_UVW.sh 3476 3651    45678   # 2002-07-09 to 2002-12-31  (36 notebooks)

# 2003-2004 (146 notebooks), seed 45678
sbatch v1.Run_parcels_UVW.sh 3656 3836    45678   # 2003-01-05 to 2003-07-04  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 3841 4021    45678   # 2003-07-09 to 2004-01-05  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 4026 4201    45678   # 2004-01-10 to 2004-07-03  (36 notebooks)
sbatch v1.Run_parcels_UVW.sh 4206 4381    45678   # 2004-07-08 to 2004-12-30  (36 notebooks)

# 2005-2006 (146 notebooks), seed 67891
sbatch v1.Run_parcels_UVW.sh 4386 4566    67891   # 2005-01-04 to 2005-07-03  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 4571 4751    67891   # 2005-07-08 to 2006-01-04  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 4756 4931    67891   # 2006-01-09 to 2006-07-03  (36 notebooks)
sbatch v1.Run_parcels_UVW.sh 4936 5111    67891   # 2006-07-08 to 2006-12-30  (36 notebooks)

# 2007-2008 (146 notebooks), seed 67891
sbatch v1.Run_parcels_UVW.sh 5116 5296    67891   # 2007-01-04 to 2007-07-03  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 5301 5481    67891   # 2007-07-08 to 2008-01-04  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 5486 5661    67891   # 2008-01-09 to 2008-07-02  (36 notebooks)
sbatch v1.Run_parcels_UVW.sh 5666 5841    67891   # 2008-07-07 to 2008-12-29  (36 notebooks)

# 2009-2010 (146 notebooks), seed 78876
sbatch v1.Run_parcels_UVW.sh 5846 6026    78876   # 2009-01-03 to 2009-07-02  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 6031 6211    78876   # 2009-07-07 to 2010-01-03  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 6216 6391    78876   # 2010-01-08 to 2010-07-02  (36 notebooks)
sbatch v1.Run_parcels_UVW.sh 6396 6571    78876   # 2010-07-07 to 2010-12-29  (36 notebooks)

# 2011-2012 (146 notebooks), seed 78876
sbatch v1.Run_parcels_UVW.sh 6576 6756    78876   # 2011-01-03 to 2011-07-02  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 6761 6941    78876   # 2011-07-07 to 2012-01-03  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 6946 7121    78876   # 2012-01-08 to 2012-07-01  (36 notebooks)
sbatch v1.Run_parcels_UVW.sh 7126 7301    78876   # 2012-07-06 to 2012-12-28  (36 notebooks)

# 2013 (73 notebooks), seed 78876
sbatch v1.Run_parcels_UVW.sh 7306 7486    78876   # 2013-01-02 to 2013-07-01  (37 notebooks)
sbatch v1.Run_parcels_UVW.sh 7491 7666    78876   # 2013-07-06 to 2013-12-28  (36 notebooks)

# total 1534 releases 1993-2013 (38 jobs after 1993-1994)
