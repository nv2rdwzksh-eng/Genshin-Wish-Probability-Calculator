#include <bits/stdc++.h>
using namespace std;
using State = tuple<int, bool, int, int>;

const double capture_radiance_base_prob = 0.00018;
const double capture_counter_2_prob = 0.10;

const int capture_counter_max = 3;
const int capture_counter_min = 0;
const int capture_counter_init = 1;
const int capture_counter_reset = 1;

// base 5-star prob (soft pity model)
double getBaseFiveStarProb(int pity) {
    if (pity >= 89) return 1.0;
    if (pity >= 73) return 0.006 + 0.06 * (pity - 72);
    return 0.006;
}

// CR model
double getCaptureRadianceProb(int captureCounter) {
    if (captureCounter >= capture_counter_max) return 1.0;
    if (captureCounter == 2) return capture_counter_2_prob;
    return capture_radiance_base_prob;
}


// core state transition
void transition(
    const State& current,
    double prob,
    map<State, double>& next
) {
    auto [pity, guaranteed, captureCount, copies] = current;
    double base_q = getBaseFiveStarProb(pity);

    if (base_q < 1.0) next[{pity + 1, guaranteed, captureCount, copies}] += prob * (1.0 - base_q);

    if (guaranteed) next[{0, false, captureCount, copies + 1}] += prob * base_q;
    
	else {
    	double captureP = getCaptureRadianceProb(captureCount);
    	double captureHit = base_q * captureP;
    	double normalHit = base_q * (1.0 - captureP);
    	
    	if (captureHit > 0.0) next[{0, false, capture_counter_reset, copies + 1}] += prob * captureHit;
    	if (normalHit > 0.0) {
    		double half = normalHit * 0.5;
    		next[{0, false, max(capture_counter_min, captureCount - 1), copies + 1}] += prob * half;
    		next[{0, true, min(capture_counter_max, captureCount + 1), copies}] += prob * half;
		}
	}
}


bool initial_Guaranteed;
int initial_Pity, initial_Copies;
int initial_CaptureCount = capture_counter_init;
int n, k;
double ans = 0.0;

int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	
	cin >> n >> k;
	map<State, double> dp;
	dp[{initial_Pity, initial_Guaranteed, initial_CaptureCount, initial_Copies}] = 1.0;

	for (int wish = 1; wish <= n; ++wish) {
		map<State, double> next;
		for (auto& [state, prob] : dp) {
			transition(state, prob, next);
		}
		dp = move(next);
	}

	for (auto [state, prob] : dp) {
		auto [pity, guaranteed, captureCount, copies] = state;
		if (copies >= k) ans += prob;
	}


	cout << fixed << setprecision(8);
	cout << "Success probability: " << ans * 100 << "\n";
	return 0;
}


// Capturing Radiance model

// IMPORTANT:
// This implementation uses a community-derived hidden-counter model.
// The hidden counter and the 10% Capturing Radiance probability at counter == 2 are community-inferred mechanics rather than officially published transition probabilities.
// Officially published information and community-derived assumptions should not be confused.

// Community model used here:
//   initial counter = 1
//   normal 50/50 win : counter -= 1 (minimum 0)
//   actual 50/50 loss: counter += 1 (maximum 3)
//   guaranteed featured 5-star: counter unchanged
//   Capturing Radiance: counter -> 1

// Capturing Radiance probabilities assumed:
//   counter 0: 0.018%
//   counter 1: 0.018%
//   counter 2: 10%
//   counter 3: 100%
