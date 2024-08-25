import math
upper = 2_097_151
lower = 0

while True:
    mid = math.ceil((lower + upper) / 2)
    print(mid, upper, lower)
    is_large = input("Large? ")

    if is_large == "1":
      lower = mid
    else:
      upper = mid