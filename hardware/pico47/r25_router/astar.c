// Multi-layer grid A* for the Pico47 continuation router.
// Node = (layer, y, x). 8-connected in-layer moves, through-via moves between any layers.
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

typedef struct { int64_t f; int32_t n; } HE;
static HE *heap; static int64_t hsz, hcap;
static void hpush(int64_t f, int32_t n) {
    if (hsz == hcap) { hcap = hcap ? hcap * 2 : 1 << 20; heap = realloc(heap, hcap * sizeof(HE)); }
    int64_t i = hsz++;
    while (i > 0) { int64_t p = (i - 1) / 2; if (heap[p].f <= f) break; heap[i] = heap[p]; i = p; }
    heap[i].f = f; heap[i].n = n;
}
static HE hpop(void) {
    HE top = heap[0], last = heap[--hsz]; int64_t i = 0;
    for (;;) { int64_t c = 2 * i + 1; if (c >= hsz) break;
        if (c + 1 < hsz && heap[c + 1].f < heap[c].f) c++;
        if (heap[c].f >= last.f) break; heap[i] = heap[c]; i = c; }
    heap[i] = last; return top;
}

// block: nl*ny*nx (nonzero = track centre forbidden). vblock: ny*nx (nonzero = via forbidden).
// extra: nl*ny*nx soft cost added on entering a node. vextra: ny*nx soft cost for a via at a cell.
// lcost: per-layer multiplier (per-mille; 1000 = 500 cost units per 0.025 mm step). starts/goal: node index lists / goal mask.
// Returns path length (nodes, written goal->start into out) or -1.
int astar(int nx, int ny, int nl, const uint8_t *block, const uint8_t *vblock,
          const int32_t *extra, const int32_t *vextra, const int32_t *lcost, int32_t via_cost,
          const int32_t *starts, int nstart, const uint8_t *goal, const double *gxs, const double *gys, const double *grads, int ngoal,
          int32_t *out, int outcap, int64_t max_expand, int32_t bend_cost) {
    int64_t N = (int64_t)nl * ny * nx, NL = (int64_t)ny * nx;
    int64_t *g = malloc(N * sizeof(int64_t)); int32_t *par = malloc(N * sizeof(int32_t));
    uint8_t *closed = calloc(N, 1);
    for (int64_t i = 0; i < N; i++) g[i] = INT64_MAX;
    hsz = 0; int minl = lcost[0]; for (int l = 1; l < nl; l++) if (lcost[l] < minl) minl = lcost[l];
    #define H(n) ({ int64_t _c = (n) % NL; int _x = _c % nx, _y = _c / nx; double best = 1e30; \
        for (int _k = 0; _k < ngoal; _k++) { double dx = fabs(_x - gxs[_k]), dy = fabs(_y - gys[_k]); \
            double d = (dx > dy ? dx + 0.41421356 * dy : dy + 0.41421356 * dx) - grads[_k]; if (d < best) best = d; } \
        if (best < 0) best = 0; (int64_t)(best * 0.5 * minl); })
    for (int i = 0; i < nstart; i++) { int32_t s = starts[i]; if (block[s]) continue; g[s] = 0; par[s] = -1; hpush(H(s), s); }
    static const int DX[8] = {1, -1, 0, 0, 1, 1, -1, -1}, DY[8] = {0, 0, 1, -1, 1, -1, 1, -1};
    static const int C[8] = {500, 500, 500, 500, 707, 707, 707, 707};
    int32_t found = -1; int64_t expanded = 0;
    while (hsz) {
        HE e = hpop(); int32_t n = e.n; if (closed[n]) continue; closed[n] = 1;
        if (goal[n]) { found = n; break; }
        if (++expanded > max_expand) break;
        int l = n / NL; int64_t c = n % NL; int x = c % nx, y = c / nx;
        int pdx = 0, pdy = 0;   // arrival direction (same layer only) for the bend penalty
        if (par[n] >= 0 && par[n] / NL == l) { int64_t pc = par[n] % NL; pdx = x - (int)(pc % nx); pdy = y - (int)(pc / nx); }
        for (int k = 0; k < 8; k++) {
            int xx = x + DX[k], yy = y + DY[k]; if (xx < 0 || yy < 0 || xx >= nx || yy >= ny) continue;
            int32_t m = (int32_t)(l * NL + (int64_t)yy * nx + xx); if (block[m] || closed[m]) continue;
            if (k >= 4) { // no squeezing diagonally between two blocked orthogonal cells
                if (block[l * NL + (int64_t)y * nx + xx] && block[l * NL + (int64_t)yy * nx + x]) continue; }
            int64_t ng = g[n] + C[k] * lcost[l] / 1000 + extra[m];
            if (pdx || pdy) {
                int dot = pdx * DX[k] + pdy * DY[k];
                int sq = (pdx * pdx + pdy * pdy) * (DX[k] * DX[k] + DY[k] * DY[k]);
                if (dot <= 0) ng += 2 * bend_cost;                 // 90 degrees or sharper
                else if (dot * dot < sq) ng += bend_cost;          // 45 degrees
            }
            if (ng < g[m]) { g[m] = ng; par[m] = n; hpush(ng + H(m), m); }
        }
        if (!vblock[c]) for (int l2 = 0; l2 < nl; l2++) {
            if (l2 == l) continue; int32_t m = (int32_t)(l2 * NL + c); if (block[m] || closed[m]) continue;
            int64_t ng = g[n] + via_cost + vextra[c] + extra[m];
            if (ng < g[m]) { g[m] = ng; par[m] = n; hpush(ng + H(m), m); }
        }
    }
    int len = -1;
    if (found >= 0) { len = 0; for (int32_t n = found; n >= 0; n = par[n]) { if (len >= outcap) { len = -2; break; } out[len++] = n; } }
    free(g); free(par); free(closed); return len;
}

// Same search restricted to the window [wx0, wx1] x [wy0, wy1] (inclusive); node indices stay global.
// Only the window is allocated and scanned, so short connections cost O(window) instead of O(board).
int astar_w(int nx, int ny, int nl, const uint8_t *block, const uint8_t *vblock,
            const int32_t *extra, const int32_t *vextra, const int32_t *lcost, int32_t via_cost,
            const int32_t *starts, int nstart, const uint8_t *goal, const double *gxs, const double *gys, const double *grads, int ngoal,
            int32_t *out, int outcap, int64_t max_expand, int32_t bend_cost, int wx0, int wy0, int wx1, int wy1) {
    int64_t NL = (int64_t)ny * nx;
    int wnx = wx1 - wx0 + 1, wny = wy1 - wy0 + 1;
    int64_t WN = (int64_t)nl * wnx * wny, WL = (int64_t)wnx * wny;
    #define LOC(n) ({ int64_t _l = (n) / NL, _c = (n) % NL; (int64_t)(_l * WL + ((_c / nx) - wy0) * wnx + ((_c % nx) - wx0)); })
    int64_t *g = malloc(WN * sizeof(int64_t)); int32_t *par = malloc(WN * sizeof(int32_t));
    uint8_t *closed = calloc(WN, 1);
    for (int64_t i = 0; i < WN; i++) g[i] = INT64_MAX;
    hsz = 0; int minl = lcost[0]; for (int l = 1; l < nl; l++) if (lcost[l] < minl) minl = lcost[l];
    #define HW(n) ({ int64_t _c = (n) % NL; int _x = _c % nx, _y = _c / nx; double best = 1e30; \
        for (int _k = 0; _k < ngoal; _k++) { double dx = fabs(_x - gxs[_k]), dy = fabs(_y - gys[_k]); \
            double d = (dx > dy ? dx + 0.41421356 * dy : dy + 0.41421356 * dx) - grads[_k]; if (d < best) best = d; } \
        if (best < 0) best = 0; (int64_t)(best * 0.5 * minl); })
    for (int i = 0; i < nstart; i++) {
        int32_t s = starts[i]; int64_t c = s % NL; int x = c % nx, y = c / nx;
        if (x < wx0 || x > wx1 || y < wy0 || y > wy1 || block[s]) continue;
        int64_t ls = LOC(s); g[ls] = 0; par[ls] = -1; hpush(HW(s), s);
    }
    static const int DX[8] = {1, -1, 0, 0, 1, 1, -1, -1}, DY[8] = {0, 0, 1, -1, 1, -1, 1, -1};
    static const int C[8] = {500, 500, 500, 500, 707, 707, 707, 707};
    int32_t found = -1; int64_t expanded = 0;
    while (hsz) {
        HE e = hpop(); int32_t n = e.n; int64_t ln = LOC(n); if (closed[ln]) continue; closed[ln] = 1;
        if (goal[n]) { found = n; break; }
        if (++expanded > max_expand) break;
        int l = n / NL; int64_t c = n % NL; int x = c % nx, y = c / nx;
        int pdx = 0, pdy = 0;
        if (par[ln] >= 0 && par[ln] / NL == l) { int64_t pc = par[ln] % NL; pdx = x - (int)(pc % nx); pdy = y - (int)(pc / nx); }
        for (int k = 0; k < 8; k++) {
            int xx = x + DX[k], yy = y + DY[k]; if (xx < wx0 || yy < wy0 || xx > wx1 || yy > wy1) continue;
            int32_t m = (int32_t)(l * NL + (int64_t)yy * nx + xx); int64_t lm = LOC(m); if (block[m] || closed[lm]) continue;
            if (k >= 4) { if (block[l * NL + (int64_t)y * nx + xx] && block[l * NL + (int64_t)yy * nx + x]) continue; }
            int64_t ng = g[ln] + C[k] * lcost[l] / 1000 + extra[m];
            if (pdx || pdy) {
                int dot = pdx * DX[k] + pdy * DY[k];
                int sq = (pdx * pdx + pdy * pdy) * (DX[k] * DX[k] + DY[k] * DY[k]);
                if (dot <= 0) ng += 2 * bend_cost; else if (dot * dot < sq) ng += bend_cost;
            }
            if (ng < g[lm]) { g[lm] = ng; par[lm] = n; hpush(ng + HW(m), m); }
        }
        if (!vblock[c]) for (int l2 = 0; l2 < nl; l2++) {
            if (l2 == l) continue; int32_t m = (int32_t)(l2 * NL + c); int64_t lm = LOC(m); if (block[m] || closed[lm]) continue;
            int64_t ng = g[ln] + via_cost + vextra[c] + extra[m];
            if (ng < g[lm]) { g[lm] = ng; par[lm] = n; hpush(ng + HW(m), m); }
        }
    }
    int len = -1;
    if (found >= 0) { len = 0; for (int32_t n = found; n >= 0; n = par[LOC(n)]) { if (len >= outcap) { len = -2; break; } out[len++] = n; } }
    free(g); free(par); free(closed); return len;
}
