#include <bits/stdc++.h>
using namespace std;

using State = tuple<int, bool, int>;

double communitySoftPityModel(int pity) {
    if (pity >= 89) return 1.0;
    if (pity >= 73) return 0.006 + 0.06 * (pity - 72);
    return 0.006;
}

int main() {
    int initialPity = 0;
    bool initialGuaranteed = false;
    int wishes = 90;

    map<State, double> dp;
    dp[{initialPity, initialGuaranteed, 0}] = 1.0;
    vector<double> pmf(wishes + 1, 0.0);

    for (int wish = 1; wish <= wishes; ++wish) {
        map<State, double> next;

        for (auto &[state, prob] : dp) {
            auto [pity, guaranteed, copies] = state;
            double q = communitySoftPityModel(pity);

            if (!guaranteed && copies == 0) pmf[wish] += prob * q;

            // No 5-star
            if (q < 1.0) {
                next[{pity + 1, guaranteed, copies}]
                    += prob * (1.0 - q);
            }

            // Got 5-star
            if (guaranteed) {
                next[{0, false, copies + 1}]
                    += prob * q;
            }

            else {
                next[{0, false, copies + 1}]
                    += prob * q * 0.5;
                next[{0, true, copies}]
                    += prob * q * 0.5;
            }
        }

        dp = next;
    }

    cout << fixed << setprecision(8);
    for (int i = 1; i <= wishes; ++i) {
        cout << "P(the " << i << "th pull) = " << pmf[i] << '\n';
    }

    double sum = 0.0;
    for (int i = 1; i <= wishes; ++i) sum += pmf[i];
    cout << "Sum of PMF = " << sum << '\n';
    return 0;
}