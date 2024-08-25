"""
Prove that any monetary amount starting
from 8 can be paid using coins of
denomination 3 and 5

Example:
  -  8 -> 3 + 5
  -  9 -> 3 + 3 + 3
  - 10 -> 5 + 5
  - 11 -> 3 + 3 + 5
"""


def get_coins(amount: int) -> list[int]:
    assert (amount > 7)

    def _get_coins(amount: int, coins: list[int]) -> list[int]:
        total = sum(coins)
        if total == amount:
            return coins

        rest = amount - total

        if rest % 5 == 0:
            coins.append(5)
        else:
            coins.append(3)
        return _get_coins(amount, coins)

    return _get_coins(amount, [])


# def change(amount: int) -> list[int]:
#     assert(amount >= 8)

#     if amount == 8:
#       return [3, 5]
    
#     if amount == 9:
#       return [3, 3, 3]

#     if amount == 10:
#       return [5, 5]

#     coins = change(amount - 3)
#     coins.append(3)
#     return coins



# for n in range(8, 30):
#     # print(n, get_coins(n))
#     print(change(n))



def change(amount):
  print('amount', amount)
  assert(amount >= 24)

  if amount == 24:
    return [5, 5, 7, 7]

  def _get_coins(amount, coins):
      total = sum(coins)
      if total == amount:
          return coins

      rest = amount - total

      if rest % 7 == 0:
          coins.append(7)
      else:
          coins.append(5)
      return _get_coins(amount, coins)

  return _get_coins(amount, [])

for amount in range(24, 50):
    print(amount, change(amount))