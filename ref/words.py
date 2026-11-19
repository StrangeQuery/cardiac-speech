"""Test words for the text machines: common English words written down for this test (no outside list), the words
of the test sentences, the exception and function words, and the number words."""
import os
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'prototype'))
import text_to_phonemes as tp   # noqa: E402
import sentences                # noqa: E402

COMMON = """
the be to of and a in that have it for not on with he as you do at this but his by from they we say her she or
an will my one all would there their what so up out if about who get which go me when make can like time no just
him know take people into year your good some could them see other than then now look only come its over think
also back after use two how our work first well way even new want because any these give day most us is was are
were been has had did does doing said says went gone done made making known knew taken took coming came looking
seen saw thought thinking used using working worked give gave given day days year years man men woman women child
children world life hand part place case week company system program question government number night point home
water room mother area money story fact month lot right study book eye job word business issue side kind head house
service friend father power hour game line end member law car city community name president team minute idea kid
body information school face others level office door health person art war history party result change morning
reason research girl guy moment air teacher force education foot boy age policy everything process music market
sense nation plan college interest death experience effect class control care field development role effort rate
heart drug show leader light voice wife police mind price report decision son view relationship town road arm
difference value building action model season society tax director position player record paper space ground form
event official matter center couple site project activity star table need court oil situation cost industry figure
street image phone data picture practice piece land product doctor wall patient worker news test movie north love
support technology step baby computer type attention film tree source organization hair window evidence population
site truth song letter machine telephone television radio cardiac decimal number seven eleven hundred thousand
million zero cat dog fish bird horse cow pig sheep goat chicken duck mouse rabbit tiger lion bear wolf fox snake
red orange yellow green blue purple black white brown gray pink gold silver happy sad angry tired hungry thirsty
quick slow fast big small large little long short tall high low hot cold warm cool young old early late easy hard
soft loud quiet bright dark clean dirty rich poor strong weak heavy light thick thin wide narrow deep shallow
walk run jump swim fly drive ride sit stand sleep eat drink cook read write sing dance play laugh cry speak talk
listen hear watch open close start stop begin finish win lose buy sell pay send bring carry throw catch push pull
because although however therefore though through thorough borough enough rough tough cough bough laugh caught
taught bought brought fought night light might right sight fight eight weight height neighbor
phone photo phrase graph physics photograph elephant
knee knife know knock knight write wrong wrap wrist whole who whom whose where what when why which while white
question nation station action mention fiction section caution patient ancient special social
judge bridge edge badge fudge huge orange change strange large charge george
chair cheese church child chocolate chose cheap character chorus school scheme
thing think thank three throw thumb this that these those there then them they
ship shop shoe shirt sure sugar ocean
measure pleasure treasure vision decision television
city cell cent circle cycle center cancel
gem giant gym gentle gin get give gift girl gold
music unique antique boutique physique technique
beautiful wonderful useful careful hopeful
readily happily easily quickly slowly finally really nearly simply
going being seeing doing saying playing staying flying trying crying
jumped walked talked looked wanted needed started ended added landed
boxes buses wishes watches judges
cats dogs books cars trees birds roads homes games
mtv fbi nasa usa ibm ufo dna cia
don't can't won't isn't it's i'm you're they're we're she's he's
hagelbarger portland cardiac columbus texas instruments
"""

WORDS = sorted(set(COMMON.split()) | {w.lower() for s in sentences.MAIN + sentences.MORE
                                       for w in re.findall(r"[A-Za-z']+", s)}
               | {w.lower() for w in tp.EXCEPTIONS} | {w.lower() for w in tp.FUNCTION_WORDS}
               | {w.lower() for w in tp.ONES + tp.TENS if w})
