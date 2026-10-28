"""Register exact population statistics by scanning every stored concrete hand."""
from array import array
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from math import factorial
from pathlib import Path
import sys

from .seven_card_dictionary import HAND_COUNT, DATA_FILENAME, MANIFEST_FILENAME, SevenCardRankDictionary


def summarize_chunks(chunks):
    counts = Counter()
    count = total = square_total = 0
    digest = hashlib.sha256()
    for block in chunks:
        if len(block) % 2:
            raise ValueError("Incomplete uint16 record")
        digest.update(block)
        values = array("H")
        values.frombytes(block)
        if sys.byteorder != "little":
            values.byteswap()
        if values and (min(values) < 1 or max(values) > 7462):
            raise ValueError("Rank outside 1..7462")
        count += len(values)
        total += sum(values)  # Python integers: exact, no float accumulation.
        square_total += sum(rank*rank for rank in values)
        counts.update(values)
    if count == 0:
        raise ValueError("No rank records")
    if total != sum(rank*n for rank, n in counts.items()):
        raise ValueError("Independent rank-sum check failed")
    if square_total != sum(rank*rank*n for rank, n in counts.items()):
        raise ValueError("Independent squared-rank-sum check failed")
    fraction = Fraction(total, count)
    variance = Fraction(square_total*count-total*total, count*count)
    with localcontext() as ctx:
        ctx.prec = 40
        decimal = str(Decimal(total)/Decimal(count))
        variance_decimal = Decimal(variance.numerator)/Decimal(variance.denominator)
        std_decimal = str(variance_decimal.sqrt())
    return dict(hand_count=count, rank_sum=total, mean_rank=total/count,
                rank_squared_sum=square_total, variance_rank=float(variance),
                standard_deviation_rank=float(variance)**0.5,
                variance_rank_decimal=str(variance_decimal), standard_deviation_rank_decimal=std_decimal,
                variance_rank_fraction=dict(numerator=variance.numerator, denominator=variance.denominator),
                variance_definition="population E[(rank-E[rank])^2]; denominator=N, not N-1",
                mean_rank_decimal=decimal,
                mean_rank_fraction=dict(numerator=fraction.numerator, denominator=fraction.denominator),
                rank_counts=dict(sorted(counts.items())), sha256=digest.hexdigest())


def register_all_hands_average(directory):
    directory = Path(directory)
    with SevenCardRankDictionary(directory) as table:
        expected_hash = table.manifest["sha256"]
        with (directory/DATA_FILENAME).open("rb") as stream:
            result = summarize_chunks(iter(lambda: stream.read(2*1000000), b""))
        if result["hand_count"] != HAND_COUNT or result["sha256"] != expected_hash:
            raise ValueError("Concrete-hand dictionary count/checksum mismatch")
    multiplicity = factorial(7)//(factorial(2)*factorial(3))
    result.update(key="all_explicit_seven_card_hands", schema_version=2,
                  wildcard_used=False, method="exhaustive scan of every concrete seven-card dictionary entry",
                  probability_measure="uniform over distinct seven-card sets", rank_order="1=strongest;7462=weakest",
                  registered_at=datetime.now(timezone.utc).isoformat(),
                  holdem_grouped=dict(group_sizes=[2,3,1,1], multiplicity=multiplicity,
                      state_count=HAND_COUNT*multiplicity, rank_sum=result["rank_sum"]*multiplicity,
                      rank_squared_sum=result["rank_squared_sum"]*multiplicity,
                      mean_rank=result["mean_rank"], variance_rank=result["variance_rank"],
                      standard_deviation_rank=result["standard_deviation_rank"],
                      method="exact constant multiplicity, not a second enumeration"))
    target = directory/'all_hands_average.json'
    temp = target.with_suffix('.json.tmp')
    temp.write_text(json.dumps(result, indent=2), encoding='utf-8')
    temp.replace(target)
    manifest_path = directory/MANIFEST_FILENAME
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['statistics_file'] = target.name
    manifest['all_hands_average_rank'] = result['mean_rank']
    manifest['all_hands_variance_rank'] = result['variance_rank']
    manifest['all_hands_standard_deviation_rank'] = result['standard_deviation_rank']
    temp = manifest_path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    temp.replace(manifest_path)
    return result
