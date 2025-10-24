## Technical Specifications

# Overview
This is an interview project for Twingate. We are to develop a MemoryManager 
that can alloc and free memory in a buffer.


# How to run tests
1. pip install -r requirements.txt
2. Stay in the root directory
3. Run: pytest -v


# Python
I choose Python because it is the language I'm most comfortable. I am using objects and lists
for storing and accessing my information. This is a simple way to manage my blocks 
and it is simple to understand when I need to alloc or free my blocks. 


# pytest
This is a good standard library for testing python code. I used a simple pytest.ini file for my config
alongside a standard requirements.txt file.


# pyenv
Using pyenv for my python environment management


# Fit-first algorithm
My alogrithm works on allocating the first free memory it can find while iterating over a list. This is a simple
approach and works for the context of this problem. 


## Improvements and changes I would make
I would first change how the fit-first algorithm works. This is fairly inefficient in a large system
because I have to traverse the list at least twice when I am searching if I can't find a free block the 
first iteration and have to do a defragmentation on my memory.

Visit the list sorts that I am doing. I am using the built in sort function, but depending
on the system I would look for better algrothims that would reduce time spent sorting. I would also 
consider adding something if I could use more memory to save sorting time. Generally speaking you can speed up 
things by adding more memory. So it would be a balancing act at what the system can manage as well as 
maintaining quality code.

Add more tests. It is very important to have sufficient tests when dealing with memory.
Too often do security issues arise when memory is not properly managed.

Revisit my threading. I have a single test, but that is not sufficient in ensuring
everything is working properly. Python has problems with threading and so I would like to do more testing
around that before deploying the code.

Added typing to my python, but I don't have mypy installed or anything to do validation checks before commiting code.
I would also setup black for my pre-commit hooks.

