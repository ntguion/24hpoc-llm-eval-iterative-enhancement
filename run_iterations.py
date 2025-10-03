#!/usr/bin/env python3
"""Run 5 complete iterations of the pipeline and track results."""

import subprocess
import json
import time
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=Path.cwd())
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - EXCEPTION: {e}")
        return False

def get_scores_from_report():
    """Extract scores from the latest report."""
    try:
        # Find the latest run directory
        run_dirs = sorted(Path("runs").glob("2025*"), reverse=True)
        if not run_dirs:
            return None
        
        latest_run = run_dirs[0]
        report_file = latest_run / "report.md"
        
        if not report_file.exists():
            return None
            
        with open(report_file) as f:
            content = f.read()
            
        # Extract scores from report
        lines = content.split('\n')
        scores = {}
        
        for line in lines:
            if 'avg=' in line and 'min=' in line and 'max=' in line:
                # Parse dimension statistics line
                parts = line.split('**')
                if len(parts) >= 3:
                    dim_name = parts[1].strip()
                    # Extract average score
                    avg_part = [p for p in parts if 'avg=' in p][0]
                    avg_score = float(avg_part.split('avg=')[1].split(',')[0])
                    scores[dim_name] = avg_score
        
        return scores
    except Exception as e:
        print(f"Error extracting scores: {e}")
        return None

def main():
    """Run 5 iterations and track results."""
    print("🚀 Starting 5-iteration pipeline experiment")
    print("📊 Tracking scores across iterations...")
    
    # Store results
    iteration_results = []
    
    for iteration in range(1, 6):
        print(f"\n{'#'*80}")
        print(f"🔄 ITERATION {iteration}/5")
        print(f"{'#'*80}")
        
        iteration_start = time.time()
        
        # Step 1: Judge current summaries
        if not run_command(".venv/bin/python -m app.cli judge --provider openai --model small --workers 3", 
                          f"Iteration {iteration}: Judge summaries"):
            print(f"❌ Iteration {iteration} failed at judge step")
            continue
            
        # Step 2: Generate report
        if not run_command(".venv/bin/python -m app.cli report", 
                          f"Iteration {iteration}: Generate report"):
            print(f"❌ Iteration {iteration} failed at report step")
            continue
            
        # Step 3: Tune prompt (with --apply to automatically apply suggestions)
        if not run_command(".venv/bin/python -m app.cli tune --provider openai --model small --apply", 
                          f"Iteration {iteration}: Tune and apply prompt improvements"):
            print(f"❌ Iteration {iteration} failed at tune step")
            continue
            
        # Step 4: Regenerate summaries with improved prompt
        if not run_command(".venv/bin/python -m app.cli summarize --provider openai --model small --workers 3", 
                          f"Iteration {iteration}: Regenerate summaries with improved prompt"):
            print(f"❌ Iteration {iteration} failed at summarize step")
            continue
        
        # Extract scores for this iteration
        scores = get_scores_from_report()
        if scores:
            iteration_results.append({
                'iteration': iteration,
                'scores': scores,
                'duration': time.time() - iteration_start
            })
            print(f"\n📊 Iteration {iteration} Results:")
            for dim, score in scores.items():
                print(f"  {dim}: {score:.2f}")
        else:
            print(f"⚠️  Could not extract scores for iteration {iteration}")
    
    # Final summary
    print(f"\n{'='*80}")
    print("📈 ITERATION EXPERIMENT COMPLETE")
    print(f"{'='*80}")
    
    if iteration_results:
        print(f"\n📊 Score Progression:")
        print(f"{'Iteration':<10} {'Coverage':<10} {'Factuality':<12} {'Actionability':<14} {'Structure':<12} {'Safety':<10} {'Avg':<8}")
        print("-" * 80)
        
        for result in iteration_results:
            scores = result['scores']
            avg = sum(scores.values()) / len(scores) if scores else 0
            print(f"{result['iteration']:<10} {scores.get('coverage', 0):<10.2f} {scores.get('factuality', 0):<12.2f} {scores.get('actionability', 0):<14.2f} {scores.get('structure_brevity', 0):<12.2f} {scores.get('safety_compliance', 0):<10.2f} {avg:<8.2f}")
        
        # Calculate improvements
        if len(iteration_results) >= 2:
            first = iteration_results[0]['scores']
            last = iteration_results[-1]['scores']
            
            print(f"\n📈 Improvements (Iteration 1 → {len(iteration_results)}):")
            for dim in first.keys():
                if dim in last:
                    improvement = last[dim] - first[dim]
                    print(f"  {dim}: {first[dim]:.2f} → {last[dim]:.2f} ({improvement:+.2f})")
            
            # Overall improvement
            first_avg = sum(first.values()) / len(first)
            last_avg = sum(last.values()) / len(last)
            total_improvement = last_avg - first_avg
            print(f"\n🎯 Overall Average: {first_avg:.2f} → {last_avg:.2f} ({total_improvement:+.2f})")
            
            if total_improvement > 0:
                print(f"✅ SUCCESS: {total_improvement:.2f} point improvement!")
            else:
                print(f"⚠️  No improvement detected")
    else:
        print("❌ No results collected")
    
    print(f"\n🏁 Experiment complete! Check runs/ directory for detailed logs.")

if __name__ == "__main__":
    main()
