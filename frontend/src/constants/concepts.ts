export interface ConceptGuide {
  id: string
  title: string
  category: string
  summary: string
  coreQuestion: string
  formulaOrRule?: string
  comparison: {
    termA: string
    termB: string
    meaningA: string
    meaningB: string
    exampleA: string
    exampleB: string
    whenToUseA: string
    whenToUseB: string
  }
  keyInsight: string
  commonPitfall: string
  memoryHook: string
}

export const CONCEPT_GUIDES: Record<string, ConceptGuide> = {
  Precision: {
    id: 'Precision',
    title: 'Precision vs. Recall',
    category: 'Evaluation Metrics',
    summary: 'Precision measures the quality and exactness of your positive predictions — when your model screams "Positive!", how often is it actually right?',
    coreQuestion: 'Out of all the items predicted positive, how many were truly positive?',
    formulaOrRule: 'Precision = True Positives / (True Positives + False Positives)',
    comparison: {
      termA: 'Precision',
      termB: 'Recall (Sensitivity)',
      meaningA: 'Focuses on minimizing False Positives (avoiding false alarms).',
      meaningB: 'Focuses on minimizing False Negatives (avoiding missed detections).',
      exampleA: 'Email Spam Filter: You don\'t want an important job offer marked as spam (high precision needed).',
      exampleB: 'Cancer Screening: You never want to miss a patient who has cancer (high recall needed).',
      whenToUseA: 'When the cost of a False Positive is very high.',
      whenToUseB: 'When the cost of a False Negative (missed case) is catastrophic.',
    },
    keyInsight: 'Precision has (TP + FP) in the denominator — it only cares about what the model guessed positive, not what was left behind.',
    commonPitfall: 'Students frequently confuse Precision with Recall because both share True Positives (TP) in the numerator. Remember: Precision = "Predicted" denominator; Recall = "Real / Reality" denominator.',
    memoryHook: 'P for Precision = P for Predicted Positives in denominator! R for Recall = R for Real (Actual) Positives in denominator!',
  },
  Recall: {
    id: 'Recall',
    title: 'Recall vs. Precision',
    category: 'Evaluation Metrics',
    summary: 'Recall (Sensitivity) measures the completeness of your search — out of all the positive cases existing in the real world, how many did your model catch?',
    coreQuestion: 'Out of all actual positive items in the dataset, how many did the model find?',
    formulaOrRule: 'Recall = True Positives / (True Positives + False Negatives)',
    comparison: {
      termA: 'Recall',
      termB: 'Precision',
      meaningA: 'Completeness: Did we retrieve all relevant items?',
      meaningB: 'Exactness: Are the retrieved items actually relevant?',
      exampleA: 'Airport Security Metal Detector: Must catch every possible weapon even if it beeps on harmless keys.',
      exampleB: 'YouTube Video Recommendations: Must be genuinely interesting even if millions of videos are not shown.',
      whenToUseA: 'When missing a positive case (False Negative) is unacceptable.',
      whenToUseB: 'When showing false alarms (False Positives) ruins user trust.',
    },
    keyInsight: 'Recall cares about the ground truth positives: TP + FN. If you predict everything as positive, Recall is 100%, but Precision drops near 0.',
    commonPitfall: 'Forgetting that high Recall can be artificially achieved by predicting "Positive" for every instance. That is why F1-Score balances both.',
    memoryHook: 'Recall = "Can you RECALL all the actual facts?" (Ground Truth denominator).',
  },
  Ridge: {
    id: 'Ridge',
    title: 'Ridge (L2) vs. Lasso (L1) Regularization',
    category: 'Machine Learning Models',
    summary: 'Regularization adds a penalty term to loss functions to prevent weights from growing too large, preventing overfitting.',
    coreQuestion: 'How does Ridge regression constrain model complexity compared to Lasso?',
    formulaOrRule: 'Ridge Loss = MSE + λ ∑(w_i)²   |   Lasso Loss = MSE + λ ∑|w_i|',
    comparison: {
      termA: 'Ridge Regression (L2)',
      termB: 'Lasso Regression (L1)',
      meaningA: 'Applies squared penalty on coefficients. Shrinks weights close to zero, but never exactly zero.',
      meaningB: 'Applies absolute value penalty. Can drive non-essential weights to exactly zero.',
      exampleA: 'When you have many correlated features and want to keep all of them with balanced weights.',
      exampleB: 'Feature Selection: When you have 1000 features and want to automatically discard irrelevant ones.',
      whenToUseA: 'Multicollinearity and dense feature sets.',
      whenToUseB: 'Sparse feature selection and high-dimensional sparse data.',
    },
    keyInsight: 'Geometrically, L1 has sharp corners on axes (causing sparsity), while L2 has smooth circular contours (shrinking weights without zeroing them).',
    commonPitfall: 'Confusing which penalty causes sparse feature selection. L1 (Lasso) = absolute value = zeros out weights. L2 (Ridge) = squares = retains all features.',
    memoryHook: 'Lasso = Loops around features and cuts them to zero! Ridge = Smooth round hills that never hit zero.',
  },
  Overfitting: {
    id: 'Overfitting',
    title: 'Overfitting vs. Underfitting (Bias-Variance)',
    category: 'Model Generalization',
    summary: 'A model must generalize to unseen data. Overfitting memorizes noise; underfitting fails to capture the underlying pattern.',
    coreQuestion: 'How do you diagnose whether a model is suffering from high variance (overfitting) or high bias (underfitting)?',
    formulaOrRule: 'Total Error = Bias² + Variance + Irreducible Noise',
    comparison: {
      termA: 'Overfitting (High Variance)',
      termB: 'Underfitting (High Bias)',
      meaningA: 'Model is too complex, fitting training noise perfectly but failing on new test data.',
      meaningB: 'Model is too simple (e.g., linear line for quadratic curve), failing on both train and test.',
      exampleA: 'Training accuracy = 99%, Test accuracy = 62%.',
      exampleB: 'Training accuracy = 55%, Test accuracy = 54%.',
      whenToUseA: 'Fix by: Regularization (L1/L2), reducing features, pruning trees, gathering more data.',
      whenToUseB: 'Fix by: Increasing model complexity, adding polynomial features, training longer.',
    },
    keyInsight: 'The signature symptom of overfitting is a large gap between training loss (low) and validation/test loss (high).',
    commonPitfall: 'Assuming that having 100% training accuracy means the model is good. In reality, it almost always indicates severe overfitting.',
    memoryHook: 'Overfit = Over-memorized the textbook but fails the exam! Underfit = Didn\'t even study the basics.',
  },
  Stack: {
    id: 'Stack',
    title: 'Stack (LIFO) vs. Queue (FIFO)',
    category: 'Data Structures',
    summary: 'Stacks and Queues are fundamental linear data structures with opposing ordering semantics for insertion and removal.',
    coreQuestion: 'Which order of removal applies to Stacks versus Queues?',
    formulaOrRule: 'Stack: LIFO (Last-In, First-Out)   |   Queue: FIFO (First-In, First-Out)',
    comparison: {
      termA: 'Stack (LIFO)',
      termB: 'Queue (FIFO)',
      meaningA: 'The last element inserted is the very first one removed (Push / Pop).',
      meaningB: 'The first element inserted is the first one removed (Enqueue / Dequeue).',
      exampleA: 'Browser Back Button, Undo history in text editor, Function call stack in recursion.',
      exampleB: 'Printer job spooler, Supermarket checkout line, Breadth-First Search (BFS).',
      whenToUseA: 'Backtracking, syntax parsing, reverse traversal, depth-first search.',
      whenToUseB: 'Buffering, breadth-first search, asynchronous message brokers, scheduling.',
    },
    keyInsight: 'In a stack, both insertion and removal happen at the same end (the top). In a queue, insertion is at the rear, removal is at the front.',
    commonPitfall: 'Confusing Push/Pop (Stack) with Enqueue/Dequeue (Queue), or associating recursion with Queue instead of Call Stack.',
    memoryHook: 'Stack of dinner plates (you take from the top = LIFO). Queue at movie ticket counter (first person in line gets served = FIFO).',
  },
  BFS: {
    id: 'BFS',
    title: 'BFS (Breadth-First) vs. DFS (Depth-First)',
    category: 'Graph Algorithms',
    summary: 'BFS and DFS are fundamental graph and tree traversal strategies that explore nodes in completely different sequences.',
    coreQuestion: 'How does the exploration strategy differ between Breadth-First and Depth-First search?',
    formulaOrRule: 'BFS uses a Queue (Level-by-level)   |   DFS uses a Stack or Recursion (Branch-to-leaf)',
    comparison: {
      termA: 'BFS (Breadth-First)',
      termB: 'DFS (Depth-First)',
      meaningA: 'Visits all immediate neighbor nodes at current depth before moving to the next level.',
      meaningB: 'Follows one branch down to the deepest leaf node before backtracking.',
      exampleA: 'Finding the shortest path in an unweighted road network; finding degrees of separation on LinkedIn.',
      exampleB: 'Solving a maze, topological sorting, finding cycles in graphs.',
      whenToUseA: 'Guaranteed shortest path in unweighted graphs; finding nearest neighbors.',
      whenToUseB: 'Exhaustive path search, puzzle solving with backtracking, topological ordering.',
    },
    keyInsight: 'BFS guarantees the shortest path (minimum number of edges) in unweighted graphs because it explores outward in concentric ripples.',
    commonPitfall: 'Using DFS to find the shortest path in an unweighted graph (it will find *a* path, but rarely the shortest).',
    memoryHook: 'BFS = Ripples in a pond (level by level, uses Queue). DFS = Spelunking down a cave tunnel to the bottom before backing up (uses Stack).',
  },
  Mean: {
    id: 'Mean',
    title: 'Mean vs. Median (Outlier Sensitivity)',
    category: 'Descriptive Statistics',
    summary: 'Mean and Median describe central tendency, but respond radically differently to skewed data and extreme outlier values.',
    coreQuestion: 'Why is the arithmetic mean sensitive to outliers, while the median remains robust?',
    formulaOrRule: 'Mean = (∑ x_i) / N   |   Median = Middle value in sorted order',
    comparison: {
      termA: 'Mean (Average)',
      termB: 'Median (50th Percentile)',
      meaningA: 'Sum of all values divided by count. Every single data point shifts the value.',
      meaningB: 'The exact physical midpoint when data is sorted. 50% of data is above, 50% below.',
      exampleA: 'Class exam scores with normal bell-curve distribution.',
      exampleB: 'Household income or house prices: Billionaires skew the mean, but median reflects normal citizen wealth.',
      whenToUseA: 'Symmetric, normally distributed data without extreme outliers.',
      whenToUseB: 'Skewed distributions or data containing massive outliers.',
    },
    keyInsight: 'A single extreme value (e.g., $100,000,000 added to a list of $50,000 salaries) will launch the Mean sky-high, but the Median only shifts by one position.',
    commonPitfall: 'Using Mean to describe typical income or prices in skewed economic datasets.',
    memoryHook: 'Mean is mean — it lets extreme bullies pull it off balance! Median is the solid median strip in the center of the road.',
  },
  Classification: {
    id: 'Classification',
    title: 'Classification vs. Regression',
    category: 'Supervised Learning',
    summary: 'The two primary tasks of supervised learning, distinguished entirely by the nature of the target output variable.',
    coreQuestion: 'What defines whether a machine learning task is Classification or Regression?',
    formulaOrRule: 'Classification: Target ∈ {Category 1, Category 2, ...}   |   Regression: Target ∈ ℝ (Continuous)',
    comparison: {
      termA: 'Classification',
      termB: 'Regression',
      meaningA: 'Predicts discrete class labels, categories, or boundaries.',
      meaningB: 'Predicts continuous numerical quantities or measurements.',
      exampleA: 'Is this transaction Fraud or Legitimate? Does this X-ray show Pneumonia or Healthy?',
      exampleB: 'Predicting tomorrow\'s temperature in °C, house price in dollars, stock valuation.',
      whenToUseA: 'When the goal is categorical decision-making or grouping.',
      whenToUseB: 'When the goal is estimating quantities, rates, or continuous values.',
    },
    keyInsight: 'Even when classification models output a probability (e.g., 0.82), the underlying target is still a discrete label, evaluated with Cross-Entropy / Log-Loss, not MSE.',
    commonPitfall: 'Thinking that Logistic Regression is a regression model because of its name — it is actually a classification algorithm!',
    memoryHook: 'Classification = Choosing a Class / Bucket. Regression = Returning a Real Number on a continuum.',
  },
}

export function getConceptGuide(topicOrSubtopic?: string | null): ConceptGuide {
  if (!topicOrSubtopic) return CONCEPT_GUIDES.Precision
  const key = Object.keys(CONCEPT_GUIDES).find(
    k => k.toLowerCase() === topicOrSubtopic.toLowerCase() ||
         topicOrSubtopic.toLowerCase().includes(k.toLowerCase())
  )
  return key ? CONCEPT_GUIDES[key] : CONCEPT_GUIDES.Precision
}
