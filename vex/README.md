# Triage of findings, and the VEX

Every finding of HIGH or CRITICAL blocks the check, also if there is no fix yet. It only passes once there is a
decision: update, remove, shield, or a statement in `openvex.json` that the image is not affected, with the reason
(MIT-41). Such a statement applies to one version of a package. When a new version comes, the finding comes back,
and you decide again.

This is the product of sub-question 2 of the research (SBOM in CI/CD): "How can vulnerable components from an SBOM
scan be triaged?"

## Why

Up to this step the scan only blocked a vulnerability with a fix (`--ignore-unfixed`). That is a decision too: accepting
all vulnerabilities without a fix, without looking at them. On the image of `main` (368a30d) there were 164, of which
44 HIGH (T-114). What those findings are worth only became clear when checking them:

- **44 findings were 8 vulnerabilities.** One vulnerability in util-linux is listed for each of the 9 packages built from util-linux.
- **None is in CISA KEV** (the list of vulnerabilities that are really exploited), and the highest EPSS score of the 8
  is 0.005: a chance of half a percent of exploitation in the next 30 days, anywhere in the world.
- **Severity and EPSS each point another way.** The highest EPSS scores (up to 0.058) belong to old glibc
  vulnerabilities of severity LOW, which the scan does not even count.
- **For 5 of the 8 the vulnerable code is not in the image, or never runs.** For the other 3, all three in mount,
  a mitigation stops it: an empty `/etc/fstab`, and since this step no setuid bit on mount anymore (MIT-42).

Severity alone therefore says little about this image. What counts is whether the vulnerable code is there, whether it
runs, and whether an attacker can reach it.

## The flow

Per vulnerability, not per finding: first group the findings of the same vulnerability.

1. **Is there a fix?** Update: Dependabot proposes a new version or digest (MIT-33), or update the digest of
   the base image yourself. Done.
2. **Is the component needed?** No: remove it from the image. That is how pip went (b31d334), with its four
   vulnerabilities (T-105). Removing is better than a statement: a component that is not there gives no new findings either.
3. **Is the vulnerability in CISA KEV, or is the EPSS score 0.1 or higher?** Then this vulnerability first, the same day:
   remove or shield. A statement alone is not enough then. The threshold of 0.1 is our own choice; on 19-10-2026 no
   finding came close.
4. **Is the vulnerable code in the image?** Check which file or program has the vulnerability, and whether the package
   contains it (`dpkg -L <package>` in the container). No: `not_affected`, with `vulnerable_code_not_present`.
5. **Does the vulnerable code run?** Check which libraries the processes of the app load (`/proc/<pid>/maps`), and
   whether the app ever starts the program. No: `not_affected`, with `vulnerable_code_not_in_execute_path`.
6. **Can an attacker still reach it, but something stops it?** For example: mount without a setuid bit, and an empty
   `/etc/fstab`. Record the mitigation in the Dockerfile, and then `not_affected` with
   `inline_mitigations_already_exist`.
7. **Otherwise the image is affected.** Set `affected` with an `action_statement`: what you are going to do, and when.
   The check then keeps failing. If something must pass anyway, only temporarily: a rule with `expired_at` in an
   ignore file of Trivy. That works (T-115), but has not been needed yet, so it is not in the workflow.

A finding of MEDIUM or LOW does not block the check. Step 3 does apply there: a vulnerability in KEV, or with a high
EPSS score, gets priority, whatever the severity. You check that by hand on the kept SBOM, as in T-114;
it does not happen automatically yet.

## Rules for `openvex.json`

- **OpenVEX 0.2.0, with a PURL per package.** A CycloneDX VEX points to one SBOM through the `serialNumber`. Trivy gives
  every SBOM a new number, also for the same image (T-114), so such a VEX would have to be redone on every build. A
  PURL stays the same as long as the package is the same.
- **Always with a version, without qualifiers.** Without a version the statement applies to every version, also one you
  never looked at (T-115). With the qualifier `distro` it falls away with every new Debian version.
- **Always a reason:** for `not_affected` a `justification` and an `impact_statement`, for `affected` an
  `action_statement`. Trivy also filters out a `not_affected` without a reason (T-115). That is why the step Check VEX
  in `image.yml` checks that first, and fails otherwise.
- **No `fixed`.** Trivy filters that out too, but whether a vulnerability is fixed shows in the version; the scan should
  see that itself.
- **Only through a pull request,** like every change on `main`. Raise `version` on every change, and set
  `last_updated`.

## What it does not solve

- **A statement can be wrong.** The check sees whether there is a reason, not whether it is right. Only whoever merges
  the pull request sees that (MC-30, step 6).
- **The work.** Every new vulnerability of HIGH or CRITICAL in Debian, also without a fix, blocks every pull request
  until there is a decision, also a pull request that only changes the BoK.
- **A vulnerability that becomes known after the build** is only seen by the scan at the next pull request or push.
- **The VEX is public.** It tells which vulnerabilities are in the image, and why we think they cannot be reached.
  That is in the SBOM too; the code and the image are already public.

## Sources

Retrieved on 19-10-2026.

- OpenVEX, specification v0.2.0 (statuses and justifications): https://github.com/openvex/spec/blob/main/OPENVEX-SPEC.md
- Trivy, VEX as a file (CycloneDX through BOM-Link with `serialNumber`, OpenVEX through PURL; "EXPERIMENTAL"): https://trivy.dev/latest/docs/supply-chain/vex/file/
- CISA, Known Exploited Vulnerabilities (catalogue 2026.10.16, 1748 vulnerabilities): https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
- FIRST, EPSS API (scores of 19-10-2026): https://api.first.org/data/v1/epss
