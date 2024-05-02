# -*- coding: utf-8 -*-

import sys

class Moirasies:

	def main(self, start, stop, atoma):

		starts = []
		ends = []
		start = int(start)
		stop = int(stop)
		atoma = int(atoma)
		results = []

		upoloipo = stop - start
		frames_per_atomo = upoloipo / atoma
		current = int(start) + int(round(frames_per_atomo))

		starts.append(start)
		ends.append(current)

		for i in range(atoma - 1):
			current += 1
			starts.append(current)
			current += int(frames_per_atomo)
			ends.append(current)

		j = 0
		k = 0

		if ends[-1] > stop:
			
			for i in ends[:-1]:
				ends[j] = i - 1
				j += 1
			for i in starts:
				starts[k] = i - 1
				k += 1

			starts[0] = start
			ends[-1] = stop

		for i in zip(starts, ends):
			results.append([i[0], i[1]])
		
		return results